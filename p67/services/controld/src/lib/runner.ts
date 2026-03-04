import type { ChildProcess } from 'node:child_process';
import * as fs from 'node:fs';
import { basename, resolve } from 'node:path';
import type { LogService } from '@controld/lib/LogService.js';
import type { Manifest } from '@controld/lib/manifest.js';
import { detectLanguage, parseManifest } from '@controld/lib/manifest.js';
import {
    createAdapter,
    type DockerAdapterConfig,
    type RuntimeAdapter,
} from '@controld/lib/runtime/adapter.js';
import {
    type InterruptMessage,
    InterruptMessageSchema,
    type Message,
    MessageType,
    makeOAuthTokenResponseMessage,
    makeResumeInterruptMessage,
    makeRunWorkflowMessage,
    type NotifyConfig,
    type RequestOAuthTokenMessage,
    RequestOAuthTokenMessageSchema,
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
    result?: unknown;
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

/**
 * Button presets for common interrupt scenarios
 */
const BUTTON_PRESETS = {
    approve_reject: [
        { label: 'Approve', value: 'approve', style: 'primary' as const },
        { label: 'Reject', value: 'reject', style: 'danger' as const },
    ],
    yes_no: [
        { label: 'Yes', value: 'yes', style: 'primary' as const },
        { label: 'No', value: 'no' },
    ],
    continue_cancel: [
        { label: 'Continue', value: 'continue', style: 'primary' as const },
        { label: 'Cancel', value: 'cancel', style: 'danger' as const },
    ],
};

/**
 * Sends a Slack notification for an interrupt
 */
async function sendSlackNotification(
    notify: NotifyConfig,
    interruptId: string,
    payload: unknown,
    valueManager: ValueManager,
    logger: Logger,
): Promise<void> {
    if (notify.type !== 'slack') {
        return;
    }

    try {
        // Resolve the OAuth token
        const accessToken = await valueManager.getOAuthToken(notify.oauthRef);

        // Get user info to determine recipient
        let channel: string;
        if (notify.recipient === 'self' || !notify.recipient) {
            // Get the user's Slack ID
            const userResponse = await fetch(
                'https://slack.com/api/users.identity',
                {
                    headers: { Authorization: `Bearer ${accessToken}` },
                },
            );
            const userData = (await userResponse.json()) as {
                ok: boolean;
                user?: { id: string };
                error?: string;
            };
            if (!userData.ok || !userData.user?.id) {
                throw new Error(
                    `Failed to get user ID: ${userData.error || 'Unknown error'}`,
                );
            }
            channel = userData.user.id;
        } else {
            // Use the specified channel/user ID
            channel = notify.recipient;
        }

        // Build the message blocks
        const blocks: unknown[] = [];

        // If custom blocks are provided, use them
        if (notify.blocks && notify.blocks.length > 0) {
            blocks.push(...notify.blocks);
        } else {
            // Build default blocks from text and buttons
            if (notify.text) {
                blocks.push({
                    type: 'section',
                    text: {
                        type: 'mrkdwn',
                        text: notify.text,
                    },
                });
            } else if (payload) {
                // Use payload as text if no text specified
                blocks.push({
                    type: 'section',
                    text: {
                        type: 'mrkdwn',
                        text:
                            typeof payload === 'string'
                                ? payload
                                : JSON.stringify(payload, null, 2),
                    },
                });
            }
        }

        // Add buttons (from preset or custom)
        const buttons =
            notify.buttons ||
            (notify.buttonPreset ? BUTTON_PRESETS[notify.buttonPreset] : null);

        if (buttons && buttons.length > 0) {
            blocks.push({
                type: 'actions',
                block_id: `interrupt_${interruptId}`,
                elements: buttons.map((btn, idx) => ({
                    type: 'button',
                    text: {
                        type: 'plain_text',
                        text: btn.label,
                        emoji: true,
                    },
                    value: JSON.stringify({
                        interruptId,
                        value: btn.value,
                    }),
                    action_id: `interrupt_action_${idx}`,
                    ...(btn.style && { style: btn.style }),
                })),
            });
        }

        // Send the message
        const response = await fetch('https://slack.com/api/chat.postMessage', {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                channel,
                text: notify.text || 'Workflow requires input',
                blocks,
            }),
        });

        const result = (await response.json()) as {
            ok: boolean;
            error?: string;
        };
        if (!result.ok) {
            throw new Error(`Slack API error: ${result.error}`);
        }

        logger.debug(`Slack notification sent for interrupt ${interruptId}`);
    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        logger.error(`Failed to send Slack notification: ${errorMsg}`);
    }
}

export class Runner {
    private workflowId: string;
    private proc: ChildProcess | null = null;
    private adapter: RuntimeAdapter | null = null;
    private currentRunId: string = 'unknown';
    private pendingInterrupt: InterruptPayload | null = null;
    private interruptResolve: ((value: RunResult) => void) | null = null;
    private completionPromise: Promise<RunResult> | null = null;
    private completionResolve: ((value: RunResult) => void) | null = null;
    private valueManager: ValueManager | null = null;
    private mergedParams: Record<string, string> = {};

    constructor(
        private readonly workflowDir: string,
        private readonly db: PrismaClient,
        private readonly userId: string,
        private readonly logService: LogService,
        private readonly params: Record<string, string>,
        private readonly sandboxConfig: DockerAdapterConfig,
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

        if (!this.proc || !this.adapter) {
            throw new Error('No active workflow process to resume');
        }

        const message = makeResumeInterruptMessage({
            interruptId,
            response,
        });

        this.adapter.sendMessage(this.proc, message);
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
     * Wait for the next workflow event (interrupt or completion) after resuming.
     * This sets up a new interrupt resolver that will be called when either:
     * 1. The workflow hits another interrupt
     * 2. The workflow completes or fails
     * @returns Promise that resolves with RunResult indicating next state
     */
    public waitForNextEvent(): Promise<RunResult> {
        return new Promise((resolve) => {
            // Set up interrupt resolver for next interrupt
            this.interruptResolve = resolve;

            // Also listen to completion promise in case workflow ends
            if (this.completionPromise) {
                this.completionPromise.then((result) => {
                    // Only resolve if we haven't already resolved via interrupt
                    // The interruptResolve will be nulled out once called
                    if (this.interruptResolve === resolve) {
                        this.interruptResolve = null;
                        resolve(result);
                    }
                });
            }
        });
    }

    /**
     * Serializes a P67Config (with Map) to a plain object for IPC.
     */
    private serializeConfig(config: P67Config): SerializedP67Config {
        return {
            snowflakeConfig: Object.fromEntries(config.snowflakeConfig),
            parameters: this.mergedParams,
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
            this.valueManager = new ValueManager(this.db, this.userId);
            hydratedConfig = await hydrateConfig(manifest, this.valueManager);
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

        // Hydrate top-level manifest params and merge with runtime params
        // Runtime params override manifest defaults
        if (manifest.params && this.valueManager) {
            for (const [key, valueObj] of Object.entries(manifest.params)) {
                try {
                    const hydratedValue = await this.valueManager.get(valueObj);
                    if (hydratedValue !== undefined) {
                        this.mergedParams[key] = hydratedValue;
                    }
                } catch (err) {
                    // For required params without runtime override, fail early
                    if (valueObj.required && !this.params?.[key]) {
                        throw new Error(
                            `Required param "${key}" could not be hydrated: ${err instanceof Error ? err.message : err}`,
                        );
                    }
                    // Log but continue - param may be overridden by runtime params
                    console.warn(
                        `Warning: Could not hydrate param "${key}":`,
                        err instanceof Error ? err.message : err,
                    );
                }
            }
        }
        // Runtime params override manifest params
        if (this.params) {
            Object.assign(this.mergedParams, this.params);
        }

        // Detect workflow language and create appropriate adapter
        const language = detectLanguage(this.workflowDir, manifest);
        const adapter = createAdapter(language, this.sandboxConfig);
        this.adapter = adapter;

        console.log(`Detected workflow language: ${language}`);

        const proc = adapter.spawn(this.workflowDir);
        this.proc = proc;

        const stdout: string[] = [];
        const stderr: string[] = [];
        const errors: WorkflowErrorMessage[] = [];
        const logger = new Logger();
        let workflowResult: unknown;

        await writeLog(
            'RuntimeHost',
            `Starting ${language} workflow execution`,
        );

        if (proc.stdout) {
            proc.stdout.on('data', (data: Buffer) => {
                const text = data.toString();
                // For Python adapter, stdout is used for IPC, so don't log raw data
                // The adapter handles message parsing
                if (language === 'typescript') {
                    console.log('[Child stdout]:', text);
                    // Don't push to stdout[] — it pollutes the response sent to callers.
                    // The structured result goes via IPC (result field).
                    // Log lines go to logger (result.log) for CLI display.
                    logger.stdout(text.trim());
                    writeLog('RuntimeHost', text.trim(), { stream: 'stdout' });
                }
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

        // Use adapter's message handling
        const handleMessage = (message: Message) => {
            // Handle 'result' messages (workflow completion)
            const msgAny = message as { type: string; data?: unknown };
            if (msgAny.type === 'result') {
                logger.debug('Received result message from child process');
                const resultData = msgAny.data;
                workflowResult = resultData;
                logger.debug(`Workflow result received`);
                writeLog('RuntimeHost', 'Workflow completed with result', {
                    result: resultData,
                });
                // For Python workflows, stdout contains IPC messages, so capture result in stdout
                if (language === 'python') {
                    stdout.push(`Result: ${JSON.stringify(resultData)}`);
                }
                return;
            }

            const msgType = msgAny.type;
            console.log(`Received message of type ${msgType}`);
            logger.debug(
                `Runner received ${msgType} message from child process`,
            );

            switch (msgType) {
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

                    // Send Slack notification if configured
                    if (interruptData.notify && this.valueManager) {
                        sendSlackNotification(
                            interruptData.notify,
                            interruptData.interruptId,
                            interruptData.payload,
                            this.valueManager,
                            logger,
                        ).catch((error) => {
                            logger.error(
                                `Slack notification error: ${error instanceof Error ? error.message : String(error)}`,
                            );
                        });
                    }

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
                            result: workflowResult,
                        });
                    }
                    break;
                }
                case MessageType.RunWorkflow:
                    console.log('Received unexpected RunWorkflow message');
                    logger.debug(
                        `Runner received unexpected RunWorkflow message from child process: ${JSON.stringify(message)}`,
                    );
                    break;
                case MessageType.ResumeInterrupt:
                    // This shouldn't happen - ResumeInterrupt goes parent -> child
                    console.log('Received unexpected ResumeInterrupt message');
                    logger.debug(
                        `Runner received unexpected ResumeInterrupt message from child process`,
                    );
                    break;
                case MessageType.RequestOAuthToken: {
                    const pm =
                        RequestOAuthTokenMessageSchema.safeParse(message);
                    if (!pm.success) {
                        console.log(
                            `Failed to parse RequestOAuthTokenMessage: ${JSON.stringify(message)}`,
                        );
                        return;
                    }
                    const oauthRequest = pm.data as RequestOAuthTokenMessage;
                    logger.debug(
                        `Resolving OAuth token: ${oauthRequest.oauthRef}`,
                    );

                    // Resolve the OAuth token using ValueManager
                    (async () => {
                        try {
                            if (!this.valueManager) {
                                throw new Error('ValueManager not initialized');
                            }
                            const accessToken =
                                await this.valueManager.getOAuthToken(
                                    oauthRequest.oauthRef,
                                );
                            const response = makeOAuthTokenResponseMessage({
                                requestId: oauthRequest.requestId,
                                accessToken,
                            });
                            adapter.sendMessage(proc, response);
                        } catch (error) {
                            const errorMsg =
                                error instanceof Error
                                    ? error.message
                                    : String(error);
                            logger.error(
                                `Failed to resolve OAuth token: ${errorMsg}`,
                            );
                            const response = makeOAuthTokenResponseMessage({
                                requestId: oauthRequest.requestId,
                                error: errorMsg,
                            });
                            adapter.sendMessage(proc, response);
                        }
                    })();
                    break;
                }
                case MessageType.OAuthTokenResponse:
                    // This shouldn't happen - OAuthTokenResponse goes parent -> child
                    console.log(
                        'Received unexpected OAuthTokenResponse message',
                    );
                    logger.debug(
                        `Runner received unexpected OAuthTokenResponse message from child process`,
                    );
                    break;
            }
        };

        // Register the message handler with the adapter
        adapter.onMessage(proc, handleMessage);

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
                    result: workflowResult,
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
                    result: workflowResult,
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
                    result: workflowResult,
                };
                // Always resolve the completion promise on exit
                this.completionResolve?.(result);
                // Only resolve getResult if we haven't already resolved due to interrupt
                if (!this.pendingInterrupt) {
                    resolve(result);
                }
                // Clean up process reference
                this.proc = null;
                this.adapter = null;
            });
        });

        adapter.sendMessage(proc, m);
        const result = await getResult;

        // Complete the run record only if workflow completed (not interrupted)
        if (this.logService && result.status !== 'interrupted') {
            await this.logService.completeRun(runId, result.exitCode);
        }

        return result;
    }
}
