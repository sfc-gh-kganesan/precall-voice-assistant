import { fork } from 'node:child_process';
import * as fs from 'node:fs';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { LogService } from '@controld/lib/LogService.js';
import type { Manifest } from '@controld/lib/manifest.js';
import { parseManifest } from '@controld/lib/manifest.js';
import {
    MessageSchema,
    MessageType,
    makeRunWorkflowMessage,
    type SerializedP67Config,
    type WorkflowError,
    type WorkflowErrorMessage,
    WorkflowErrorMessageSchema,
} from '@controld/lib/runtime/schema.js';
import { hydrateConfig } from '@controld/lib/sdk-impl.js';
import { ValueManager } from '@controld/lib/value-manager.js';
import type { PrismaClient } from '@p67/db';
import type { P67Config } from '@p67/workflow-sdk';

export type RunResult = {
    stdout: string[];
    stderr: string[];
    log: string[];
    exitCode: number;
    errors: Array<{ error: WorkflowError; message: string }>;
    runId: string;
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

    constructor(
        private readonly workflowDir: string,
        private readonly db: PrismaClient,
        private readonly userId: string,
        private readonly logService?: LogService,
    ) {
        // Extract workflow ID from directory name (e.g., "wf-abc123")
        this.workflowId = basename(workflowDir);
    }

    /**
     * Serializes a P67Config (with Map) to a plain object for IPC.
     */
    private serializeConfig(config: P67Config): SerializedP67Config {
        return {
            snowflakeConfig: Object.fromEntries(config.snowflakeConfig),
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
            };
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
            };
        }

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
            config: this.serializeConfig(hydratedConfig),
        });

        const getExitCode = new Promise<number>((resolve) => {
            proc.on('error', (error) => {
                console.error('child process error:', error);
                logger.debug(
                    `Runner received error message from child process: ${error}`,
                );
                writeLog('RuntimeHost', `Process error: ${error}`, {
                    error: 'ProcessError',
                });
                resolve(1);
            });

            proc.on('uncaughtException', (error) => {
                console.error('child process uncaught exception:', error);
                logger.debug(
                    `Runner received uncaught exception from child process: ${error}`,
                );
                writeLog('RuntimeHost', `Uncaught exception: ${error}`, {
                    error: 'UncaughtException',
                });
                resolve(1);
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
                resolve(code || 0);
            });
        });

        proc.send(m);
        const exitCode = await getExitCode;

        // Complete the run record
        if (this.logService) {
            await this.logService.completeRun(runId, exitCode);
        }

        return {
            stdout,
            stderr,
            log: logger.dump(),
            errors,
            exitCode,
            runId,
        };
    }
}
