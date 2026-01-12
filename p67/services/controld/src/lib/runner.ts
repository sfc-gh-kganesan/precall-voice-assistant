import { fork } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
    MessageSchema,
    MessageType,
    makeRunWorkflowMessage,
    type WorkflowError,
    type WorkflowErrorMessage,
    WorkflowErrorMessageSchema,
} from '@controld/lib/runtime/schema.js';

export type RunResult = {
    stdout: string[];
    stderr: string[];
    log: string[];
    exitCode: number;
    errors: Array<{ error: WorkflowError; message: string }>;
};

export class Logger {
    private lines: string[] = [];

    public debug(msg: string): void {
        this.addLine('🔧', msg);
    }

    public stderr(msg: string): void {
        this.addLine('🟡', msg);
    }

    public stdout(msg: string): void {
        this.addLine('🟢', msg);
    }

    public error(msg: string): void {
        this.addLine('🔴', msg);
    }

    private addLine(prefix: string, msg: string): void {
        const prefixWidth = 3;
        const padding = ' '.repeat(Math.max(0, prefixWidth - prefix.length));
        this.lines.push(`${prefix}${padding}|  ${msg}`);
    }

    public dump(): string[] {
        return this.lines;
    }
}

export class Runner {
    constructor(private readonly workflowDir: string) {}

    public async start(): Promise<RunResult> {
        console.log(`Running workflow from ${this.workflowDir}...`);
        const __filename = fileURLToPath(import.meta.url);
        const __dirname = dirname(__filename);
        const hostPath = resolve(__dirname, 'runtime', 'host.js');

        const proc = fork(hostPath, [], {
            stdio: ['pipe', 'pipe', 'pipe', 'ipc'],
        });

        const stdout: string[] = [];
        const stderr: string[] = [];
        const errors: WorkflowErrorMessage[] = [];
        const logger = new Logger();

        if (proc.stdout) {
            proc.stdout.on('data', (data: Buffer) => {
                const text = data.toString();
                console.log('[Child stdout]:', text);
                stdout.push(text);
                logger.stdout(text.trim());
            });
        }

        if (proc.stderr) {
            proc.stderr.on('data', (data: Buffer) => {
                const text = data.toString();
                console.error('[Child stderr]:', text);
                stderr.push(text);
                logger.stderr(text.trim());
            });
        }

        proc.on('message', (message) => {
            const m = MessageSchema.safeParse(message);
            if (!m.success) {
                console.log(
                    `Failed to parse message: ${JSON.stringify(message)}`,
                );

                logger.debug(
                    `Runner received invalid message from child process: ${JSON.stringify(message)}`,
                );
                return;
            }

            console.log(`Received message of type ${m.data.type}`);
            logger.debug(
                `Runner received ${m.data.type} message from child process`,
            );

            switch (m.data.type) {
                case MessageType.ThrowError: {
                    const pm = WorkflowErrorMessageSchema.safeParse(message);
                    if (!pm.success) {
                        console.log(
                            `Failed to parse WorkflowErrorMessage: ${JSON.stringify(message)}`,
                        );
                        logger.debug(
                            `Runner received invalid WorkflowErrorMessage from child process`,
                        );
                        return;
                    }
                    logger.error(`${pm.data.error}: ${pm.data.message}`);
                    errors.push(pm.data);
                    break;
                }
                case MessageType.RunWorkflow:
                    console.log('Received unexpected RunWorkflow message');
                    logger.debug(
                        `Runner received unexpected RunWorkflow message from child process: ${JSON.stringify(m.data)}`,
                    );
                    break;
            }
        });

        const m = makeRunWorkflowMessage({
            dir: this.workflowDir,
        });

        const getExitCode = new Promise<number>((resolve) => {
            proc.on('error', (error) => {
                console.error('child process error:', error);
                logger.debug(
                    `Runner received error message from child process: ${error}`,
                );
                resolve(1);
            });

            proc.on('uncaughtException', (error) => {
                console.error('child process uncaught exception:', error);
                logger.debug(
                    `Runner received uncaught exception from child process: ${error}`,
                );
                resolve(1);
            });

            proc.on('exit', (code) => {
                console.log(`Child process exited with code ${code}`);
                logger.debug(`Child process exited with code ${code}`);
                resolve(code || 0);
            });
        });

        proc.send(m);
        const exitCode = await getExitCode;

        return {
            stdout,
            stderr,
            log: logger.dump(),
            errors,
            exitCode,
        };
    }
}
