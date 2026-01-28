import type { ChildProcess } from 'node:child_process';
import { fork } from 'node:child_process';
import * as fs from 'node:fs';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { LogService } from '@controld/lib/LogService.js';
import type { Manifest } from '@controld/lib/manifest.js';
import { parseManifest } from '@controld/lib/manifest.js';
import {
    type InterruptMessage,
    InterruptMessageSchema,
    MessageSchema,
    MessageType,
    makeResumeInterruptMessage,
    makeRunWorkflowMessage,
    type SerializedP67Config,
    type WorkflowError,
    type WorkflowErrorMessage,
    WorkflowErrorMessageSchema,
} from '@controld/lib/runtime/schema.js';
import { hydrateConfig } from '@controld/lib/sdk-impl.js';
import { ValueManager } from '@controld/lib/value-manager.js';
import type { PrismaClient } from '@p67/db';
import type { InterruptPayload, P67Config } from '@p67/workflow-sdk';

export type RunStatus = 'running' | 'completed' | 'interrupted' | 'failed';

export type RunResult = {
    stdout: string[];
    stderr: string[];
    log: string[];
    exitCode: number;
    errors: Array<{ error: WorkflowError; message: string }>;
    runId: string;
    status: RunStatus;
    pendingInterrupt?: InterruptPayload;
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
    private workflowId: string;
    private proc: ChildProcess | null = null;
    private currentRunId: string = 'unknown';
    private pendingInterrupt: InterruptPayload | null = null;
    private interruptResolve: ((value: RunResult) => void) | null = null;
    private completionPromise: Promise<RunResult> | null = null;
    private completionResolve: ((value: RunResult) => void) | null = null;

    constructor(
        private readonly workflowDir: string,
        private readonly db: PrismaClient,
        private readonly userId: string,
        private readonly logService?: LogService,
        private readonly params?: Record<string, string>,
    ) {
        // Extract workflow ID from directory name (e.g., "wf-abc123")
        this.workflowId = basename(workflowDir);
        this.params = params;
    }

    /**
     * Returns the current pending interrupt, if any
     */
    public getPendingInterrupt(): InterruptPayload | null {
        return this.pendingInterrupt;
    }

    /**
     * Returns whether the workflow is currently paused waiting for human input
     */
    public isInterrupted(): boolean {
        return this.pendingInterrupt !== null;
    }

    /**
     * Returns the current run ID
     */
    public getRunId(): string {
        return this.currentRunId;
    }

    /**
     * Returns the workflow ID
     */
    public getWorkflowId(): string {
        return this.workflowId;
    }

    /**
     * Resume a paused workflow with human input
     * @param interruptId - The ID of the interrupt to resume
     * @param response - The response from the human
     * @throws Error if no interrupt is pending or IDs don't match
     */
    public resume(interruptId: string, response: unknown): void {
        if (!this.pendingInterrupt) {
            throw new Error('No pending interrupt to resume');
        }

        if (this.pendingInterrupt.interruptId !== interruptId) {
            throw new Error(
                `Interrupt ID mismatch: expected ${this.pendingInterrupt.interruptId}, got ${interruptId}`,
            );
        }

        if (!this.proc) {
            throw new Error('No active workflow process to resume');
        }

        const message = makeResumeInterruptMessage({
            interruptId,
            response,
        });

        this.proc.send(message);
        this.pendingInterrupt = null;
    }

    /**
     * Wait for workflow completion after resuming from an interrupt
     * @returns Promise that resolves with the final RunResult
     * @throws Error if no completion promise is available (workflow not started or already completed)
     */
    public waitForCompletion(): Promise<RunResult> {
        if (!this.completionPromise) {
            throw new Error(
                'No active workflow to wait for completion. Either start() was not called or workflow already completed.',
            );
        }
        return this.completionPromise;
    }

    /**
     * Serializes a P67Config (with Map) to a plain object for IPC.
     */
    private serializeConfig(config: P67Config): SerializedP67Config {
        return {
            snowflakeConfig: Object.fromEntries(config.snowflakeConfig),
            parameters: this.params ?? {},
        };
    }

    public async start(): Promise<RunResult> {
        console.log(`Running workflow from ${this.workflowDir}...`);

        // Create a workflow run record if logService is available
        let runId = 'unknown';
        if (this.logService) {
            const run = await this.logService.createRun(
                this.workflowId,
                this.userId,
            );
            runId = run.id;
        }
        this.currentRunId = runId;

        // Helper to write logs to the database
        const writeLog = async (
            source: 'RuntimeHost' | 'WorkflowNode' | 'ToolCall',
            message: string,
            attributes?: Record<string, unknown>,
        ) => {
            if (this.logService) {
                await this.logService.writeLog({
                    runId,
                    workflowId: this.workflowId,
                    userId: this.userId,
                    source,
                    message,
                    attributes,
                });
            }
        };

        // Load and parse manifest
        const manifestPath = resolve(this.workflowDir, 'manifest.yaml');
        if (!fs.existsSync(manifestPath)) {
            const errorMsg = `Manifest not found at ${manifestPath}`;
            await writeLog('RuntimeHost', errorMsg, {
                error: 'ManifestNotfound',
            });
            if (this.logService) {
                await this.logService.completeRun(runId, 1);
            }
            return {
                stdout: [],
                stderr: [],
                log: [errorMsg],
                exitCode: 1,
                errors: [
                    {
                        error: 'ManifestNotfound' as WorkflowError,
                        message: `${manifestPath} does not exist`,
                    },
                ],
                runId,
                status: 'failed',
            };
        }

        let manifestStr: string;
        try {
            manifestStr = await fs.promises.readFile(manifestPath, 'utf-8');
        } catch (err) {
            const message =
                err instanceof Error ? err.message : 'Unknown error';
            const errorMsg = `Failed to read manifest: ${message}`;
            await writeLog('RuntimeHost', errorMsg, {
                error: 'ManifestLoadParseError',
            });
            if (this.logService) {
                await this.logService.completeRun(runId, 1);
            }
            return {
                stdout: [],
                stderr: [],
                log: [errorMsg],
                exitCode: 1,
                errors: [
                    {
                        error: 'ManifestLoadParseError' as WorkflowError,
                        message,
                    },
                ],
                runId,
                status: 'failed',
            };
        }

        let manifest: Manifest;
        try {
            manifest = parseManifest(manifestStr);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : 'Unknown error';
            const errorMsg = `Failed to parse manifest: ${message}`;
            await writeLog('RuntimeHost', errorMsg, {
                error: 'ManifestLoadParseError',
            });
            if (this.logService) {
                await this.logService.completeRun(runId, 1);
            }
            return {
                stdout: [],
                stderr: [],
                log: [errorMsg],
                exitCode: 1,
                errors: [
                    {
                        error: 'ManifestLoadParseError' as WorkflowError,
                        message,
                    },
                ],
                runId,
                status: 'failed',
            };
        }

        // Override manifest parameters with CLI-provided params
        for (const config of manifest.config) {
            if (config.parameters) {
                for (const [key, value] of Object.entries(this.params ?? {})) {
                    if (key in config.parameters) {
                        config.parameters[key] = { value };
                    }
                }
            }
        }

        // Hydrate config using ValueManager
        let hydratedConfig: P67Config;
        try {
            const valueManager = new ValueManager(this.db, this.userId);
            hydratedConfig = await hydrateConfig(manifest, valueManager);
        } catch (err) {
            const message =
                err instanceof Error ? err.message : 'Unknown error';
            const errorMsg = `Failed to hydrate config: ${message}`;
            await writeLog('RuntimeHost', errorMsg, {
                error: 'ExecutionError',
            });
            if (this.logService) {
                await this.logService.completeRun(runId, 1);
            }
            return {
                stdout: [],
                stderr: [],
                log: [errorMsg],
                exitCode: 1,
                errors: [
                    {
                        error: 'ExecutionError' as WorkflowError,
                        message: `Config hydration failed: ${message}`,
                    },
                ],
                runId,
                status: 'failed',
            };
        }

        const __filename = fileURLToPath(import.meta.url);
        const __dirname = dirname(__filename);
        const hostPath = resolve(__dirname, 'runtime', 'host.js');

        const proc = fork(hostPath, [], {
            stdio: ['pipe', 'pipe', 'pipe', 'ipc'],
        });
        this.proc = proc;

        const stdout: string[] = [];
        const stderr: string[] = [];
        const errors: WorkflowErrorMessage[] = [];
        const logger = new Logger();

        await writeLog('RuntimeHost', 'Starting workflow execution');

        if (proc.stdout) {
            proc.stdout.on('data', (data: Buffer) => {
                const text = data.toString();
                console.log('[Child stdout]:', text);
                stdout.push(text);
                logger.stdout(text.trim());
                writeLog('RuntimeHost', text.trim(), { stream: 'stdout' });
            });
        }

        if (proc.stderr) {
            proc.stderr.on('data', (data: Buffer) => {
                const text = data.toString();
                console.error('[Child stderr]:', text);
                stderr.push(text);
                logger.stderr(text.trim());
                writeLog('RuntimeHost', text.trim(), { stream: 'stderr' });
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
                    writeLog(
                        'RuntimeHost',
                        `${pm.data.error}: ${pm.data.message}`,
                        {
                            error: pm.data.error,
                        },
                    );
                    break;
                }
                case MessageType.Interrupt: {
                    const pm = InterruptMessageSchema.safeParse(message);
                    if (!pm.success) {
                        console.log(
                            `Failed to parse InterruptMessage: ${JSON.stringify(message)}`,
                        );
                        logger.debug(
                            `Runner received invalid InterruptMessage from child process`,
                        );
                        return;
                    }
                    const interruptData = pm.data as InterruptMessage;
                    logger.debug(
                        `Workflow interrupted: ${interruptData.interruptId}`,
                    );

                    // Store the pending interrupt
                    this.pendingInterrupt = {
                        interruptId: interruptData.interruptId,
                        value: interruptData.payload,
                        timestamp: interruptData.timestamp,
                        nodeId: interruptData.nodeId,
                    };

                    writeLog(
                        'RuntimeHost',
                        `Workflow waiting for human input: ${interruptData.interruptId}`,
                        {
                            interruptId: interruptData.interruptId,
                            payload: interruptData.payload,
                            nodeId: interruptData.nodeId,
                        },
                    );

                    // If we have an interrupt resolver, call it to return early
                    if (this.interruptResolve) {
                        this.interruptResolve({
                            stdout,
                            stderr,
                            log: logger.dump(),
                            errors,
                            exitCode: -1, // Special code indicating interrupted
                            runId,
                            status: 'interrupted',
                            pendingInterrupt: this.pendingInterrupt,
                        });
                    }
                    break;
                }
                case MessageType.RunWorkflow:
                    console.log('Received unexpected RunWorkflow message');
                    logger.debug(
                        `Runner received unexpected RunWorkflow message from child process: ${JSON.stringify(m.data)}`,
                    );
                    break;
                case MessageType.ResumeInterrupt:
                    // This shouldn't happen - ResumeInterrupt goes parent -> child
                    console.log('Received unexpected ResumeInterrupt message');
                    logger.debug(
                        `Runner received unexpected ResumeInterrupt message from child process`,
                    );
                    break;
            }
        });

        const m = makeRunWorkflowMessage({
            dir: this.workflowDir,
            config: this.serializeConfig(hydratedConfig),
        });

        // Create a completion promise that resolves only when process exits
        this.completionPromise = new Promise<RunResult>((resolve) => {
            this.completionResolve = resolve;
        });

        // Create a promise that resolves on exit OR on interrupt (for early return from start())
        const getResult = new Promise<RunResult>((resolve) => {
            // Store resolve for interrupt handler to use
            this.interruptResolve = resolve;

            proc.on('error', (error) => {
                console.error('child process error:', error);
                logger.debug(
                    `Runner received error message from child process: ${error}`,
                );
                writeLog('RuntimeHost', `Process error: ${error}`, {
                    error: 'ProcessError',
                });
                const result: RunResult = {
                    stdout,
                    stderr,
                    log: logger.dump(),
                    errors,
                    exitCode: 1,
                    runId,
                    status: 'failed',
                };
                resolve(result);
                this.completionResolve?.(result);
            });

            proc.on('uncaughtException', (error) => {
                console.error('child process uncaught exception:', error);
                logger.debug(
                    `Runner received uncaught exception from child process: ${error}`,
                );
                writeLog('RuntimeHost', `Uncaught exception: ${error}`, {
                    error: 'UncaughtException',
                });
                const result: RunResult = {
                    stdout,
                    stderr,
                    log: logger.dump(),
                    errors,
                    exitCode: 1,
                    runId,
                    status: 'failed',
                };
                resolve(result);
                this.completionResolve?.(result);
            });

            proc.on('exit', (code) => {
                console.log(`Child process exited with code ${code}`);
                logger.debug(`Child process exited with code ${code}`);
                writeLog(
                    'RuntimeHost',
                    `Workflow completed with exit code ${code}`,
                    {
                        exitCode: code,
                    },
                );
                const result: RunResult = {
                    stdout,
                    stderr,
                    log: logger.dump(),
                    errors,
                    exitCode: code || 0,
                    runId,
                    status: code === 0 ? 'completed' : 'failed',
                };
                // Always resolve the completion promise on exit
                this.completionResolve?.(result);
                // Only resolve getResult if we haven't already resolved due to interrupt
                if (!this.pendingInterrupt) {
                    resolve(result);
                }
                // Clean up process reference
                this.proc = null;
            });
        });

        proc.send(m);
        const result = await getResult;

        // Complete the run record only if workflow completed (not interrupted)
        if (this.logService && result.status !== 'interrupted') {
            await this.logService.completeRun(runId, result.exitCode);
        }

        return result;
    }
}
