/**
 * Runtime Adapter
 *
 * Provides a unified interface for spawning and communicating with
 * workflow runtime hosts across different languages (TypeScript, Python).
 * All workflows run inside the p67-runner Docker container.
 */

import type { ChildProcess } from 'node:child_process';
import { spawn } from 'node:child_process';
import type { Message } from '@controld/lib/runtime/schema.js';

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
 * Shared NDJSON-over-stdout message handling for adapters that
 * communicate via stdin/stdout.
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
 * Docker-based runtime adapter (Python + TypeScript).
 * Runs the p67-runner container with the workflow directory bind-mounted.
 * The Go supervisor inside the container auto-detects the language
 * (main.py vs index.js) and execs the appropriate host process.
 * IPC is NDJSON over stdin/stdout for both languages.
 */
export class DockerAdapter implements RuntimeAdapter {
    readonly language: WorkflowLanguage;

    private readonly ndjson = new NdjsonMessageHandler();

    constructor(
        language: WorkflowLanguage,
        private readonly image: string,
        private readonly hostStorageRoot?: string,
        private readonly containerStorageRoot?: string,
    ) {
        this.language = language;
    }

    spawn(workflowDir?: string): ChildProcess {
        if (!workflowDir) {
            throw new Error(
                'DockerAdapter requires workflowDir to be passed to spawn()',
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

export type DockerAdapterConfig = {
    runnerImage: string;
    hostStorageRoot?: string;
    containerStorageRoot?: string;
};

/**
 * Create a DockerAdapter for the given workflow language.
 */
export function createAdapter(
    language: WorkflowLanguage,
    config: DockerAdapterConfig,
): RuntimeAdapter {
    return new DockerAdapter(
        language,
        config.runnerImage,
        config.hostStorageRoot,
        config.containerStorageRoot,
    );
}
