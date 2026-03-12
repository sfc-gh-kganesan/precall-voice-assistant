import type { SandboxConfig } from '@controld/config.js';
import type { PrismaClient } from '@p67/db';
import { LogLevel, SocketModeClient } from '@slack/socket-mode';
import type { LogService } from './LogService.js';
import type { Runner } from './runner.js';
import {
    executeCommand,
    parseCommand,
    type SlackSlashCommandPayload,
} from './slack-commands.js';

/**
 * Slack interactive message payload structure for block_actions
 */
interface SlackBlockActionsPayload {
    type: 'block_actions';
    user: {
        id: string;
        username: string;
        name: string;
        team_id: string;
    };
    api_app_id: string;
    container: {
        type: string;
        message_ts: string;
        channel_id: string;
    };
    channel: {
        id: string;
        name: string;
    };
    message: {
        ts: string;
        text: string;
    };
    response_url: string;
    actions: Array<{
        type: string;
        action_id: string;
        block_id: string;
        value: string;
    }>;
}

/**
 * Parsed button value from our interrupt buttons
 */
interface InterruptButtonValue {
    interruptId: string;
    value: unknown;
}

/**
 * Registry type for managing active workflow runners
 */
type RunnerRegistry = Map<string, Runner>;

/**
 * SlackSocketModeService handles Slack interactive events via WebSocket connection.
 * This eliminates the need for a public webhook URL.
 */
export class SlackSocketModeService {
    private socketModeClient: SocketModeClient | null = null;
    private isRunning = false;

    constructor(
        private readonly db: PrismaClient,
        private readonly runnerRegistry: RunnerRegistry,
        private readonly logService: LogService,
        private readonly sandboxConfig: SandboxConfig,
        private readonly appToken?: string,
    ) {}

    /**
     * Start the Socket Mode connection to Slack
     */
    async start(): Promise<void> {
        const appToken = this.appToken || process.env.SLACK_APP_TOKEN;

        if (!appToken) {
            console.log(
                '⚠️  SLACK_APP_TOKEN not set - Slack Socket Mode disabled',
            );
            return;
        }

        this.socketModeClient = new SocketModeClient({
            appToken,
            logLevel: LogLevel.DEBUG,
            pingPongLoggingEnabled: false,
            clientOptions: {
                slackApiUrl: 'https://api.slack.com/api/',
            },
        });

        this.socketModeClient.on(
            'slack_event',
            (event: { type: string; body: unknown; envelope_id: string }) => {
                console.log(
                    `📨 Raw slack_event received: type=${event.type}, envelope_id=${event.envelope_id}`,
                );
            },
        );

        // Listen for interactive events (button clicks, modal submissions, etc.)
        this.socketModeClient.on(
            'interactive',
            async ({
                body,
                ack,
            }: {
                body: SlackBlockActionsPayload;
                ack: (response?: unknown) => Promise<void>;
            }) => {
                // Acknowledge immediately - Slack requires this within 3 seconds
                await ack();

                if (body.type === 'block_actions') {
                    await this.handleBlockActions(body);
                }
            },
        );

        // Listen for slash commands (e.g., /workflow run my-workflow)
        this.socketModeClient.on(
            'slash_commands',
            async ({
                body,
                ack,
            }: {
                body: SlackSlashCommandPayload;
                ack: (response?: unknown) => Promise<void>;
            }) => {
                console.log(
                    `📥 Received slash command: ${body.command} ${body.text}`,
                );

                // Parse and execute the command
                const parsedCommand = parseCommand(body.text);
                const result = await executeCommand(parsedCommand, body, {
                    db: this.db,
                    runnerRegistry: this.runnerRegistry,
                    logService: this.logService,
                    sandboxConfig: this.sandboxConfig,
                });

                if (result.message || result.blocks) {
                    await ack({
                        response_type: 'ephemeral',
                        text: result.message || ' ',
                        blocks: result.blocks,
                    });
                } else {
                    await ack();
                }

                // If the command kicked off async work (like running a workflow),
                // further updates will be sent via response_url in executeCommand
            },
        );

        // Handle connection events
        this.socketModeClient.on('connected', () => {
            console.log('✅ Slack Socket Mode connected');
        });

        this.socketModeClient.on('disconnected', () => {
            console.log('⚠️  Slack Socket Mode disconnected');
        });

        this.socketModeClient.on('error', (error) => {
            console.error('❌ Slack Socket Mode error:', error);
        });

        try {
            await this.socketModeClient.start();
            this.isRunning = true;
            console.log('🔌 Slack Socket Mode service started');
        } catch (error) {
            console.error('Failed to start Slack Socket Mode:', error);
        }
    }

    /**
     * Stop the Socket Mode connection
     */
    async stop(): Promise<void> {
        if (this.socketModeClient && this.isRunning) {
            await this.socketModeClient.disconnect();
            this.isRunning = false;
            console.log('🔌 Slack Socket Mode service stopped');
        }
    }

    /**
     * Handle block_actions events (button clicks)
     */
    private async handleBlockActions(
        body: SlackBlockActionsPayload,
    ): Promise<void> {
        for (const action of body.actions) {
            // Check if this is an interrupt action
            if (!action.block_id.startsWith('interrupt_')) {
                continue;
            }

            // Parse the button value to get interruptId and response value
            let buttonValue: InterruptButtonValue;
            try {
                buttonValue = JSON.parse(action.value);
            } catch {
                console.error(`Failed to parse button value: ${action.value}`);
                continue;
            }

            const { interruptId, value } = buttonValue;

            console.log(
                `📥 Received Slack button click for interrupt: ${interruptId}`,
            );

            // Find the interrupt in the database
            const interrupt = await this.db.workflowInterrupt.findUnique({
                where: { id: interruptId },
            });

            if (!interrupt) {
                await this.updateMessage(body.response_url, {
                    text: `⚠️ Interrupt not found: ${interruptId}`,
                    replace_original: true,
                });
                continue;
            }

            if (interrupt.status !== 'Pending') {
                await this.updateMessage(body.response_url, {
                    text: `✓ Already processed (status: ${interrupt.status})`,
                    replace_original: true,
                });
                continue;
            }

            // Get the runner from the registry
            const runner = this.runnerRegistry.get(interrupt.runId);
            if (!runner) {
                await this.updateMessage(body.response_url, {
                    text: '⚠️ Workflow process no longer active. The workflow may have timed out or crashed.',
                    replace_original: true,
                });
                continue;
            }

            // Resume the workflow
            runner.resume(interruptId, value);

            // Update the interrupt record
            const resumedAt = new Date();
            await this.db.workflowInterrupt.update({
                where: { id: interruptId },
                data: {
                    status: 'Resumed',
                    response: value as object,
                    resumedAt,
                },
            });

            // Update the Slack message to show completion
            await this.updateMessage(body.response_url, {
                text: `✓ Response received: ${typeof value === 'string' ? value : JSON.stringify(value)}`,
                replace_original: true,
            });

            // Handle workflow continuation asynchronously
            this.handleWorkflowContinuation(runner, interrupt).catch(
                (error) => {
                    console.error(
                        'Error handling workflow continuation:',
                        error,
                    );
                },
            );
        }
    }

    /**
     * Update a Slack message using the response_url
     */
    private async updateMessage(
        responseUrl: string,
        message: {
            text: string;
            replace_original?: boolean;
            blocks?: unknown[];
        },
    ): Promise<void> {
        try {
            await fetch(responseUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(message),
            });
        } catch (error) {
            console.error('Failed to update Slack message:', error);
        }
    }

    /**
     * Handle workflow continuation after an interrupt is resumed
     */
    private async handleWorkflowContinuation(
        runner: Runner,
        interrupt: { runId: string; workflowId: string },
    ): Promise<void> {
        const nextResult = await runner.waitForNextEvent();

        if (
            nextResult.status === 'interrupted' &&
            nextResult.pendingInterrupt
        ) {
            // Workflow hit another interrupt - save it to database
            await this.db.workflowInterrupt.create({
                data: {
                    id: nextResult.pendingInterrupt.interruptId,
                    runId: interrupt.runId,
                    workflowId: interrupt.workflowId,
                    payload: nextResult.pendingInterrupt.value as object,
                    nodeId: nextResult.pendingInterrupt.nodeId,
                    status: 'Pending',
                },
            });

            // Update run status to Interrupted
            await this.db.workflowRun.update({
                where: { id: interrupt.runId },
                data: { status: 'Interrupted' },
            });
        } else {
            // Workflow completed or failed
            await this.db.workflowRun.update({
                where: { id: interrupt.runId },
                data: {
                    status:
                        nextResult.status === 'completed'
                            ? 'Completed'
                            : 'Failed',
                    completedAt: new Date(),
                },
            });

            // Clean up runner from registry
            this.runnerRegistry.delete(interrupt.runId);
        }
    }

    /**
     * Check if the service is currently running
     */
    isConnected(): boolean {
        return this.isRunning;
    }
}
