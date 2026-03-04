import { existsSync } from 'node:fs';
import type { PrismaClient } from '@p67/db';
import type { LogService } from './LogService.js';
import { Runner } from './runner.js';
import type { DockerAdapterConfig } from './runtime/adapter.js';
import {
    addReaction,
    postMessage,
    removeReaction,
    updateMessage,
} from './slack-client.js';

/**
 * Slack slash command payload structure
 */
export interface SlackSlashCommandPayload {
    command: string; // e.g., "/workflow"
    text: string; // Everything after the command
    user_id: string; // Slack user ID
    user_name: string; // Slack username
    team_id: string; // Slack workspace ID
    team_domain: string; // Slack workspace domain
    channel_id: string; // Channel where command was issued
    channel_name: string; // Channel name
    response_url: string; // URL for async responses
    trigger_id: string; // For opening modals
}

/**
 * Parsed workflow command
 */
export interface ParsedCommand {
    action: 'run' | 'list' | 'status' | 'link' | 'help' | 'unknown';
    workflowId?: string;
    runId?: string;
    params?: Record<string, string>;
    raw: string;
}

/**
 * Result of command execution
 */
export interface CommandResult {
    success: boolean;
    message: string;
    blocks?: unknown[]; // Slack Block Kit blocks for rich formatting
}

/**
 * Dependencies for command execution
 */
export interface CommandDependencies {
    db: PrismaClient;
    runnerRegistry: Map<string, Runner>;
    logService: LogService;
    sandboxConfig: DockerAdapterConfig;
    linkBaseUrl?: string; // Base URL for account linking
}

/**
 * Parse a slash command text into structured command
 *
 * Supported formats:
 * - run <workflow-id> [param1=value1 param2=value2]
 * - list
 * - status <run-id>
 * - link
 * - help
 */
export function parseCommand(text: string): ParsedCommand {
    const trimmed = text.trim();
    const parts = trimmed.split(/\s+/);
    const action = parts[0]?.toLowerCase() || '';

    switch (action) {
        case 'run': {
            const workflowId = parts[1];
            const params: Record<string, string> = {};

            // Parse key=value params
            for (let i = 2; i < parts.length; i++) {
                const param = parts[i];
                const eqIndex = param.indexOf('=');
                if (eqIndex > 0) {
                    const key = param.substring(0, eqIndex);
                    const value = param.substring(eqIndex + 1);
                    params[key] = value;
                }
            }

            return {
                action: 'run',
                workflowId,
                params: Object.keys(params).length > 0 ? params : undefined,
                raw: trimmed,
            };
        }

        case 'list':
            return { action: 'list', raw: trimmed };

        case 'status': {
            const runId = parts[1];
            return { action: 'status', runId, raw: trimmed };
        }

        case 'link':
            return { action: 'link', raw: trimmed };

        case 'help':
        case '':
            return { action: 'help', raw: trimmed };

        default:
            return { action: 'unknown', raw: trimmed };
    }
}

/**
 * Execute a parsed slash command
 */
export async function executeCommand(
    command: ParsedCommand,
    slackPayload: SlackSlashCommandPayload,
    deps: CommandDependencies,
): Promise<CommandResult> {
    switch (command.action) {
        case 'run':
            return executeRunCommand(command, slackPayload, deps);

        case 'list':
            return executeListCommand(slackPayload, deps);

        case 'status':
            return executeStatusCommand(command, slackPayload, deps);

        case 'link':
            return executeLinkCommand(slackPayload, deps);

        case 'help':
            return executeHelpCommand();

        default:
            return {
                success: false,
                message: `Unknown command: \`${command.raw}\`. Type \`/workflow help\` for available commands.`,
            };
    }
}

/**
 * Execute the 'run' command
 */
async function executeRunCommand(
    command: ParsedCommand,
    slackPayload: SlackSlashCommandPayload,
    deps: CommandDependencies,
): Promise<CommandResult> {
    if (!command.workflowId) {
        return {
            success: false,
            message:
                'Missing workflow ID. Usage: `/workflow run <workflow-id> [param1=value1]`',
        };
    }

    // Look up the P67 user linked to this Slack user
    const slackUser = await deps.db.slackUser.findUnique({
        where: {
            slackUserId_slackTeamId: {
                slackUserId: slackPayload.user_id,
                slackTeamId: slackPayload.team_id,
            },
        },
        include: { user: true },
    });

    if (!slackUser) {
        return {
            success: false,
            message:
                'Your Slack account is not linked to P67. Use `/workflow link` to connect your account.',
        };
    }

    // Find the workflow
    const workflow = await deps.db.workflow.findFirst({
        where: {
            id: command.workflowId,
            OR: [{ ownerId: slackUser.userId }, { visibility: 'Public' }],
        },
    });

    if (!workflow) {
        return {
            success: false,
            message: `Workflow \`${command.workflowId}\` not found or you don't have access to it.`,
        };
    }

    if (!existsSync(workflow.storagePath)) {
        return {
            success: false,
            message: `Workflow \`${command.workflowId}\` storage not found on disk.`,
        };
    }

    // Post initial message to channel to start a thread
    const initialMessage = await postMessage(
        slackPayload.channel_id,
        `:hourglass_flowing_sand: *Running workflow* \`${command.workflowId}\``,
    );

    if (!initialMessage.ok || !initialMessage.ts) {
        // Fall back to response_url if we can't post directly
        console.warn(
            'Could not post initial message, falling back to response_url',
        );
        return {
            success: true,
            message: `⏳ Starting workflow \`${command.workflowId}\`... (thread unavailable)`,
        };
    }

    const threadTs = initialMessage.ts;
    const channelId = slackPayload.channel_id;

    // Add running reaction
    await addReaction(channelId, threadTs, 'runner');

    // Start the workflow asynchronously
    const runnerInstance = new Runner(
        workflow.storagePath,
        deps.db,
        slackUser.userId,
        deps.logService,
        command.params || {},
        deps.sandboxConfig,
    );

    // Don't await - let it run in background and post updates to thread
    runWorkflowAsync(
        runnerInstance,
        workflow.id,
        command.workflowId,
        channelId,
        threadTs,
        deps,
    ).catch((error) => {
        console.error('Error running workflow from Slack:', error);
        // Update the original message with error
        updateMessage(
            channelId,
            threadTs,
            `:x: *Workflow* \`${command.workflowId}\` *failed to start*\nError: ${error instanceof Error ? error.message : 'Unknown error'}`,
        );
        removeReaction(channelId, threadTs, 'runner');
        addReaction(channelId, threadTs, 'x');
    });

    // Return empty - we've already posted the initial message
    return {
        success: true,
        message: '', // Don't send ephemeral response since we posted to channel
    };
}

/**
 * Thread context for Slack messages
 */
interface SlackThreadContext {
    channelId: string;
    threadTs: string;
}

/**
 * Run workflow and send updates to Slack thread
 */
async function runWorkflowAsync(
    runner: Runner,
    workflowId: string,
    workflowName: string,
    channelId: string,
    threadTs: string,
    deps: CommandDependencies,
): Promise<void> {
    const ctx: SlackThreadContext = { channelId, threadTs };

    const result = await runner.start();

    // Register runner for potential interrupt handling
    if (result.runId) {
        deps.runnerRegistry.set(result.runId, runner);
    }

    // Post STDOUT to thread if there's output
    if (result.stdout && result.stdout.length > 0) {
        const stdout = result.stdout.join('\n');
        if (stdout.trim()) {
            await postMessage(
                ctx.channelId,
                `\`\`\`${stdout.slice(0, 2900)}\`\`\``,
                {
                    threadTs: ctx.threadTs,
                },
            );
        }
    }

    // Post STDERR to thread if there's error output
    if (result.stderr && result.stderr.length > 0) {
        const stderr = result.stderr.join('\n');
        if (stderr.trim()) {
            await postMessage(
                ctx.channelId,
                `:warning: *stderr:*\n\`\`\`${stderr.slice(0, 2900)}\`\`\``,
                {
                    threadTs: ctx.threadTs,
                },
            );
        }
    }

    if (result.status === 'interrupted' && result.pendingInterrupt) {
        // Workflow hit an interrupt - create the interrupt record
        await deps.db.workflowInterrupt.create({
            data: {
                id: result.pendingInterrupt.interruptId,
                runId: result.runId,
                workflowId: workflowId,
                payload: result.pendingInterrupt.value as object,
                nodeId: result.pendingInterrupt.nodeId,
                status: 'Pending',
            },
        });

        await deps.db.workflowRun.update({
            where: { id: result.runId },
            data: { status: 'Interrupted' },
        });

        // Update original message to show paused state
        await updateMessage(
            ctx.channelId,
            ctx.threadTs,
            `:double_vertical_bar: *Workflow* \`${workflowName}\` *paused - awaiting input*`,
        );
        await removeReaction(ctx.channelId, ctx.threadTs, 'runner');
        await addReaction(ctx.channelId, ctx.threadTs, 'hourglass');

        // Post interrupt buttons to thread
        await postMessage(ctx.channelId, 'Workflow requires input:', {
            threadTs: ctx.threadTs,
            blocks: buildInterruptBlocks(result.pendingInterrupt),
        });

        // Set up completion handler
        handleWorkflowCompletion(runner, result.runId, workflowName, ctx, deps);
    } else if (result.exitCode === 0) {
        // Success - update original message
        await updateMessage(
            ctx.channelId,
            ctx.threadTs,
            `:white_check_mark: *Workflow* \`${workflowName}\` *completed successfully*\nRun ID: \`${result.runId}\``,
        );
        await removeReaction(ctx.channelId, ctx.threadTs, 'runner');
        await addReaction(ctx.channelId, ctx.threadTs, 'white_check_mark');
        deps.runnerRegistry.delete(result.runId);
    } else {
        // Failure - update original message
        const errorMsg =
            result.errors.length > 0
                ? result.errors.map((e) => e.message).join(', ')
                : 'Unknown error';
        await updateMessage(
            ctx.channelId,
            ctx.threadTs,
            `:x: *Workflow* \`${workflowName}\` *failed*\nError: ${errorMsg}`,
        );
        await removeReaction(ctx.channelId, ctx.threadTs, 'runner');
        await addReaction(ctx.channelId, ctx.threadTs, 'x');
        deps.runnerRegistry.delete(result.runId);
    }
}

/**
 * Handle workflow completion after interrupts
 */
function handleWorkflowCompletion(
    runner: Runner,
    runId: string,
    workflowName: string,
    ctx: SlackThreadContext,
    deps: CommandDependencies,
): void {
    runner
        .waitForCompletion()
        .then(async (finalResult) => {
            deps.runnerRegistry.delete(runId);

            await deps.db.workflowRun.update({
                where: { id: runId },
                data: {
                    status:
                        finalResult.status === 'completed'
                            ? 'Completed'
                            : 'Failed',
                    completedAt: new Date(),
                },
            });

            // Remove hourglass, add final status
            await removeReaction(ctx.channelId, ctx.threadTs, 'hourglass');

            if (finalResult.status === 'completed') {
                await updateMessage(
                    ctx.channelId,
                    ctx.threadTs,
                    `:white_check_mark: *Workflow* \`${workflowName}\` *completed successfully*`,
                );
                await addReaction(
                    ctx.channelId,
                    ctx.threadTs,
                    'white_check_mark',
                );
            } else {
                await updateMessage(
                    ctx.channelId,
                    ctx.threadTs,
                    `:x: *Workflow* \`${workflowName}\` *failed*`,
                );
                await addReaction(ctx.channelId, ctx.threadTs, 'x');
            }
        })
        .catch((err) => {
            console.error('Error waiting for workflow completion:', err);
            deps.runnerRegistry.delete(runId);
        });
}

/**
 * Build Slack Block Kit blocks for an interrupt
 */
function buildInterruptBlocks(interrupt: {
    interruptId: string;
    value: unknown;
    nodeId?: string;
}): unknown[] {
    const payload = interrupt.value as {
        question?: string;
        options?: Array<{ label: string; value: unknown }>;
    };

    const blocks: unknown[] = [
        {
            type: 'section',
            text: {
                type: 'mrkdwn',
                text: payload.question || 'Workflow requires input:',
            },
        },
    ];

    // If options are provided, create buttons
    if (payload.options && Array.isArray(payload.options)) {
        const buttons = payload.options.slice(0, 5).map((opt, index) => ({
            type: 'button',
            text: {
                type: 'plain_text',
                text: opt.label || `Option ${index + 1}`,
                emoji: true,
            },
            value: JSON.stringify({
                interruptId: interrupt.interruptId,
                value: opt.value,
            }),
            action_id: `interrupt_action_${index}`,
        }));

        blocks.push({
            type: 'actions',
            block_id: `interrupt_${interrupt.interruptId}`,
            elements: buttons,
        });
    }

    return blocks;
}

/**
 * Execute the 'list' command
 */
async function executeListCommand(
    slackPayload: SlackSlashCommandPayload,
    deps: CommandDependencies,
): Promise<CommandResult> {
    // Look up the P67 user
    const slackUser = await deps.db.slackUser.findUnique({
        where: {
            slackUserId_slackTeamId: {
                slackUserId: slackPayload.user_id,
                slackTeamId: slackPayload.team_id,
            },
        },
    });

    if (!slackUser) {
        return {
            success: false,
            message:
                'Your Slack account is not linked to P67. Use `/workflow link` to connect your account.',
        };
    }

    const workflows = await deps.db.workflow.findMany({
        where: {
            OR: [{ ownerId: slackUser.userId }, { visibility: 'Public' }],
        },
        orderBy: { updatedAt: 'desc' },
        take: 20,
    });

    if (workflows.length === 0) {
        return {
            success: true,
            message:
                'No workflows found. Deploy a workflow first using the P67 CLI.',
        };
    }

    const workflowList = workflows
        .map((w) => `• \`${w.id}\` (${w.visibility.toLowerCase()})`)
        .join('\n');

    return {
        success: true,
        message: `*Available Workflows:*\n${workflowList}\n\nUse \`/workflow run <id>\` to execute a workflow.`,
    };
}

/**
 * Execute the 'status' command
 */
async function executeStatusCommand(
    command: ParsedCommand,
    slackPayload: SlackSlashCommandPayload,
    deps: CommandDependencies,
): Promise<CommandResult> {
    if (!command.runId) {
        return {
            success: false,
            message: 'Missing run ID. Usage: `/workflow status <run-id>`',
        };
    }

    const slackUser = await deps.db.slackUser.findUnique({
        where: {
            slackUserId_slackTeamId: {
                slackUserId: slackPayload.user_id,
                slackTeamId: slackPayload.team_id,
            },
        },
    });

    if (!slackUser) {
        return {
            success: false,
            message:
                'Your Slack account is not linked to P67. Use `/workflow link` to connect your account.',
        };
    }

    const run = await deps.db.workflowRun.findFirst({
        where: {
            id: command.runId,
            userId: slackUser.userId,
        },
        include: {
            workflow: true,
            interrupts: {
                where: { status: 'Pending' },
                take: 1,
            },
        },
    });

    if (!run) {
        return {
            success: false,
            message: `Run \`${command.runId}\` not found or you don't have access to it.`,
        };
    }

    const statusEmoji: Record<string, string> = {
        Running: '🔄',
        Completed: '✅',
        Failed: '❌',
        Cancelled: '⏹️',
        Interrupted: '⏸️',
    };

    let message = `*Workflow Run Status*\n`;
    message += `• ID: \`${run.id}\`\n`;
    message += `• Workflow: \`${run.workflowId}\`\n`;
    message += `• Status: ${statusEmoji[run.status] || '❓'} ${run.status}\n`;
    message += `• Started: ${run.startedAt.toISOString()}\n`;

    if (run.completedAt) {
        message += `• Completed: ${run.completedAt.toISOString()}\n`;
    }

    if (run.interrupts.length > 0) {
        message += `\n⚠️ Workflow is waiting for input.`;
    }

    return {
        success: true,
        message,
    };
}

/**
 * Execute the 'link' command
 */
async function executeLinkCommand(
    slackPayload: SlackSlashCommandPayload,
    deps: CommandDependencies,
): Promise<CommandResult> {
    // Check if already linked
    const existingLink = await deps.db.slackUser.findUnique({
        where: {
            slackUserId_slackTeamId: {
                slackUserId: slackPayload.user_id,
                slackTeamId: slackPayload.team_id,
            },
        },
        include: { user: true },
    });

    if (existingLink) {
        return {
            success: true,
            message: `Your Slack account is already linked to P67 user \`${existingLink.user.snowflakeUser}\`.`,
        };
    }

    // Generate a link token (stored temporarily)
    const linkToken = crypto.randomUUID();
    const baseUrl =
        deps.linkBaseUrl || process.env.P67_WEB_URL || 'http://localhost:5173';
    const linkUrl = `${baseUrl}/auth/slack-link?token=${linkToken}&slack_user=${slackPayload.user_id}&slack_team=${slackPayload.team_id}`;

    // Store the pending link token (expires in 10 minutes)
    // In production, you'd store this in Redis or the database
    // For now, we'll use an in-memory store with expiration
    pendingLinkTokens.set(linkToken, {
        slackUserId: slackPayload.user_id,
        slackTeamId: slackPayload.team_id,
        slackUsername: slackPayload.user_name,
        expiresAt: Date.now() + 10 * 60 * 1000,
    });

    return {
        success: true,
        message: `To link your Slack account to P67, click here:\n${linkUrl}\n\n_This link expires in 10 minutes._`,
    };
}

/**
 * Execute the 'help' command
 */
function executeHelpCommand(): CommandResult {
    const helpText = `*P67 Workflow Commands*

\`/workflow run <workflow-id> [params]\`
  Run a workflow. Parameters are optional key=value pairs.
  Example: \`/workflow run data-pipeline customer=acme\`

\`/workflow list\`
  List all workflows you have access to.

\`/workflow status <run-id>\`
  Check the status of a workflow run.

\`/workflow link\`
  Link your Slack account to your P67 account.

\`/workflow help\`
  Show this help message.`;

    return {
        success: true,
        message: helpText,
    };
}

/**
 * Send a response to Slack using response_url
 */
export async function sendSlackResponse(
    responseUrl: string,
    message: {
        text: string;
        blocks?: unknown[];
        replace_original?: boolean;
        response_type?: 'in_channel' | 'ephemeral';
    },
): Promise<void> {
    try {
        await fetch(responseUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                response_type: message.response_type || 'ephemeral',
                ...message,
            }),
        });
    } catch (error) {
        console.error('Failed to send Slack response:', error);
    }
}

/**
 * In-memory store for pending link tokens
 * In production, use Redis or database with TTL
 */
export const pendingLinkTokens = new Map<
    string,
    {
        slackUserId: string;
        slackTeamId: string;
        slackUsername: string;
        expiresAt: number;
    }
>();

/**
 * Clean up expired link tokens (call periodically)
 */
export function cleanupExpiredTokens(): void {
    const now = Date.now();
    for (const [token, data] of pendingLinkTokens) {
        if (data.expiresAt < now) {
            pendingLinkTokens.delete(token);
        }
    }
}

// Clean up expired tokens every 5 minutes
setInterval(cleanupExpiredTokens, 5 * 60 * 1000);
