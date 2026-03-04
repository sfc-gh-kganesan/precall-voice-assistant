/**
 * Runtime Adapter
 *
 * Provides a unified interface for spawning and communicating with
 * workflow runtime hosts across different languages (TypeScript, Python).
 */

import type { ChildProcess } from 'node:child_process';
import { fork, spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Message } from '@controld/lib/runtime/schema.js';
import { MessageSchema } from '@controld/lib/runtime/schema.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export type WorkflowLanguage = 'typescript' | 'python';

/**
 * Interface for runtime adapters that handle language-specific
 * process spawning and IPC.
 */
export interface RuntimeAdapter {
    /** The language this adapter handles */
    readonly language: WorkflowLanguage;

    /** Spawn the runtime host process */
    spawn(workflowDir?: string): ChildProcess;

    /** Send a message to the child process */
    sendMessage(proc: ChildProcess, message: Message): void;

    /** Set up message handling from the child process */
    onMessage(proc: ChildProcess, handler: (msg: Message) => void): void;
}

/**
 * TypeScript/JavaScript runtime adapter.
 * Uses Node.js fork() with built-in IPC channel.
 */
export class TypeScriptAdapter implements RuntimeAdapter {
    readonly language: WorkflowLanguage = 'typescript';

    private readonly hostPath: string;

    constructor() {
        this.hostPath = resolve(__dirname, 'host.js');
    }

    spawn(): ChildProcess {
        return fork(this.hostPath, [], {
            stdio: ['pipe', 'pipe', 'pipe', 'ipc'],
        });
    }

    sendMessage(proc: ChildProcess, message: Message): void {
        proc.send(message);
    }

    onMessage(proc: ChildProcess, handler: (msg: Message) => void): void {
        proc.on('message', (rawMessage: unknown) => {
            const parsed = MessageSchema.safeParse(rawMessage);
            if (parsed.success) {
                handler(parsed.data);
            } else {
                // For non-schema messages (like 'result'), pass through
                handler(rawMessage as Message);
            }
        });
    }
}

/**
 * Shared NDJSON-over-stdout message handling for adapters that
 * communicate via stdin/stdout (Python, Docker).
 */
class NdjsonMessageHandler {
    private messageBuffer: Map<ChildProcess, string> = new Map();

    sendMessage(proc: ChildProcess, message: Message): void {
        if (proc.stdin) {
            proc.stdin.write(`${JSON.stringify(message)}\n`);
        }
    }

    onMessage(
        proc: ChildProcess,
        handler: (msg: Message) => void,
        label: string,
    ): void {
        if (!proc.stdout) return;

        this.messageBuffer.set(proc, '');

        proc.stdout.on('data', (data: Buffer) => {
            let buffer = this.messageBuffer.get(proc) || '';
            buffer += data.toString();

            const lines = buffer.split('\n');
            this.messageBuffer.set(proc, lines.pop() || '');

            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const msg = JSON.parse(line);
                    handler(msg as Message);
                } catch {
                    console.log(`[${label} stdout]:`, line);
                }
            }
        });

        proc.on('exit', () => {
            this.messageBuffer.delete(proc);
        });
    }
}

/**
 * Python runtime adapter.
 * Uses spawn() with JSON over stdin/stdout for IPC.
 */
export class PythonAdapter implements RuntimeAdapter {
    readonly language: WorkflowLanguage = 'python';

    private readonly hostPath: string;
    private readonly ndjson = new NdjsonMessageHandler();

    constructor() {
        this.hostPath = resolve(__dirname, 'host.py');
    }

    spawn(): ChildProcess {
        return spawn('python3', [this.hostPath], {
            stdio: ['pipe', 'pipe', 'pipe'],
        });
    }

    sendMessage(proc: ChildProcess, message: Message): void {
        this.ndjson.sendMessage(proc, message);
    }

    onMessage(proc: ChildProcess, handler: (msg: Message) => void): void {
        this.ndjson.onMessage(proc, handler, 'Python');
    }
}

/**
 * Docker-based Python runtime adapter.
 * Runs the p67-runner container with the workflow directory bind-mounted.
 * IPC is identical to PythonAdapter: NDJSON over stdin/stdout.
 */
export class DockerPythonAdapter implements RuntimeAdapter {
    readonly language: WorkflowLanguage = 'python';

    private readonly ndjson = new NdjsonMessageHandler();

    constructor(
        private readonly image: string,
        private readonly hostStorageRoot?: string,
        private readonly containerStorageRoot?: string,
    ) {}

    spawn(workflowDir?: string): ChildProcess {
        if (!workflowDir) {
            throw new Error(
                'DockerPythonAdapter requires workflowDir to be passed to spawn()',
            );
        }

        // Translate container path to host path for Docker bind mount
        let mountPath = workflowDir;
        if (this.hostStorageRoot && this.containerStorageRoot) {
            mountPath = workflowDir.replace(
                this.containerStorageRoot,
                this.hostStorageRoot,
            );
        }

        return spawn(
            'docker',
            [
                'run',
                '--rm',
                '-i',
                '-v',
                `${mountPath}:/workflow:ro`,
                this.image,
                '/workflow',
            ],
            { stdio: ['pipe', 'pipe', 'pipe'] },
        );
    }

    sendMessage(proc: ChildProcess, message: Message): void {
        this.ndjson.sendMessage(proc, message);
    }

    onMessage(proc: ChildProcess, handler: (msg: Message) => void): void {
        this.ndjson.onMessage(proc, handler, 'Docker');
    }
}

export type SandboxConfig = {
    enabled: boolean;
    runnerImage: string;
    hostStorageRoot?: string;
    containerStorageRoot?: string;
};

/**
 * Factory function to create the appropriate adapter for a workflow language.
 * When sandbox mode is enabled, Python workflows run inside a Docker container.
 */
export function createAdapter(
    language: WorkflowLanguage,
    sandbox?: SandboxConfig,
): RuntimeAdapter {
    switch (language) {
        case 'typescript':
            return new TypeScriptAdapter();
        case 'python':
            if (sandbox?.enabled) {
                return new DockerPythonAdapter(
                    sandbox.runnerImage,
                    sandbox.hostStorageRoot,
                    sandbox.containerStorageRoot,
                );
            }
            return new PythonAdapter();
        default:
            throw new Error(`Unsupported workflow language: ${language}`);
    }
}
