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
    spawn(): ChildProcess;

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
 * Python runtime adapter.
 * Uses spawn() with JSON over stdin/stdout for IPC.
 */
export class PythonAdapter implements RuntimeAdapter {
    readonly language: WorkflowLanguage = 'python';

    private readonly hostPath: string;
    private messageBuffer: Map<ChildProcess, string> = new Map();

    constructor() {
        this.hostPath = resolve(__dirname, 'host.py');
    }

    spawn(): ChildProcess {
        return spawn('python3', [this.hostPath], {
            stdio: ['pipe', 'pipe', 'pipe'],
        });
    }

    sendMessage(proc: ChildProcess, message: Message): void {
        if (proc.stdin) {
            proc.stdin.write(`${JSON.stringify(message)}\n`);
        }
    }

    onMessage(proc: ChildProcess, handler: (msg: Message) => void): void {
        if (!proc.stdout) return;

        // Initialize buffer for this process
        this.messageBuffer.set(proc, '');

        proc.stdout.on('data', (data: Buffer) => {
            // Append to buffer
            let buffer = this.messageBuffer.get(proc) || '';
            buffer += data.toString();

            // Process complete lines (NDJSON)
            const lines = buffer.split('\n');
            // Keep the last incomplete line in the buffer
            this.messageBuffer.set(proc, lines.pop() || '');

            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const msg = JSON.parse(line);
                    handler(msg as Message);
                } catch {
                    // Not valid JSON - might be regular stdout output
                    // Log it but don't crash
                    console.log('[Python stdout]:', line);
                }
            }
        });

        proc.on('exit', () => {
            this.messageBuffer.delete(proc);
        });
    }
}

/**
 * Factory function to create the appropriate adapter for a workflow language.
 */
export function createAdapter(language: WorkflowLanguage): RuntimeAdapter {
    switch (language) {
        case 'typescript':
            return new TypeScriptAdapter();
        case 'python':
            return new PythonAdapter();
        default:
            throw new Error(`Unsupported workflow language: ${language}`);
    }
}
