import crypto from 'node:crypto';
import {
    executeCommand,
    parseCommand,
    type SlackSlashCommandPayload,
} from '@controld/lib/slack-commands.js';
import type { FastifyInstance, FastifyRequest } from 'fastify';

/**
 * Verifies that a request is actually from Slack using the signing secret.
 * See: https://api.slack.com/authentication/verifying-requests-from-slack
 */
function verifySlackSignature(
    request: FastifyRequest,
    signingSecret: string,
): boolean {
    const timestamp = request.headers['x-slack-request-timestamp'] as string;
    const signature = request.headers['x-slack-signature'] as string;

    if (!timestamp || !signature) {
        return false;
    }

    // Protect against replay attacks - request must be within 5 minutes
    const fiveMinutesAgo = Math.floor(Date.now() / 1000) - 60 * 5;
    if (parseInt(timestamp, 10) < fiveMinutesAgo) {
        return false;
    }

    // Get raw body - Fastify stores it if configured
    const rawBody = (request as unknown as { rawBody?: string }).rawBody || '';

    // Compute expected signature
    const sigBasestring = `v0:${timestamp}:${rawBody}`;
    const mySignature =
        'v0=' +
        crypto
            .createHmac('sha256', signingSecret)
            .update(sigBasestring)
            .digest('hex');

    // Constant-time comparison to prevent timing attacks
    return crypto.timingSafeEqual(
        Buffer.from(mySignature),
        Buffer.from(signature),
    );
}

/**
 * Slack interactive message payload structure
 */
interface SlackInteractionPayload {
    type: 'block_actions' | 'message_actions' | 'shortcut';
    user: {
        id: string;
        username: string;
        name: string;
        team_id: string;
    };
    api_app_id: string;
    token: string;
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

export function registerSlackWebhookRoutes(server: FastifyInstance) {
    /**
     * Slack Interactive Messages webhook endpoint
     * Receives button clicks from Slack messages sent by workflow interrupts
     *
     * Note: This endpoint must be publicly accessible and registered as an
     * "Interactivity Request URL" in your Slack app settings.
     */
    server.post(
        '/webhook/slack/interactions',
        {
            schema: {
                description: 'Slack interactive messages webhook',
                tags: ['Webhook'],
            },
            // Skip authentication - Slack calls this endpoint directly
            config: {
                skipAuth: true,
            },
        },
        async (request, reply) => {
            try {
                const signingSecret = server.config.slack.signingSecret;
                if (signingSecret) {
                    if (!verifySlackSignature(request, signingSecret)) {
                        console.error('Invalid Slack signature');
                        return reply
                            .code(401)
                            .send({ error: 'Invalid signature' });
                    }
                }

                const body = request.body as { payload?: string };
                if (!body.payload) {
                    return reply.code(400).send({ error: 'Missing payload' });
                }

                const payload: SlackInteractionPayload = JSON.parse(
                    body.payload,
                );

                // Only handle block_actions (button clicks)
                if (payload.type !== 'block_actions') {
                    return reply.code(200).send({ ok: true });
                }

                // Process each action (usually just one)
                for (const action of payload.actions) {
                    // Check if this is an interrupt action
                    if (!action.block_id.startsWith('interrupt_')) {
                        continue;
                    }

                    // Parse the button value to get interruptId and response value
                    let buttonValue: InterruptButtonValue;
                    try {
                        buttonValue = JSON.parse(action.value);
                    } catch {
                        console.error(
                            `Failed to parse button value: ${action.value}`,
                        );
                        continue;
                    }

                    const { interruptId, value } = buttonValue;

                    // Find the interrupt in the database
                    const interrupt =
                        await server.db.workflowInterrupt.findUnique({
                            where: { id: interruptId },
                        });

                    if (!interrupt) {
                        // Update message to show error
                        await updateSlackMessage(payload.response_url, {
                            text: `⚠️ Interrupt not found: ${interruptId}`,
                            replace_original: true,
                        });
                        continue;
                    }

                    if (interrupt.status !== 'Pending') {
                        // Already handled
                        await updateSlackMessage(payload.response_url, {
                            text: `✓ Already processed (status: ${interrupt.status})`,
                            replace_original: true,
                        });
                        continue;
                    }

                    // Get the runner from the registry
                    const runner = server.runnerRegistry?.get(interrupt.runId);
                    if (!runner) {
                        await updateSlackMessage(payload.response_url, {
                            text: '⚠️ Workflow process no longer active. The workflow may have timed out or crashed.',
                            replace_original: true,
                        });
                        continue;
                    }

                    // Resume the workflow
                    runner.resume(interruptId, value);

                    // Update the interrupt record
                    const resumedAt = new Date();
                    await server.db.workflowInterrupt.update({
                        where: { id: interruptId },
                        data: {
                            status: 'Resumed',
                            response: value as object,
                            resumedAt,
                        },
                    });

                    // Update the Slack message to show completion
                    await updateSlackMessage(payload.response_url, {
                        text: `✓ Response received: ${typeof value === 'string' ? value : JSON.stringify(value)}`,
                        replace_original: true,
                    });

                    // Wait for next event asynchronously (don't block Slack response)
                    handleWorkflowContinuation(server, runner, interrupt).catch(
                        (error) => {
                            console.error(
                                'Error handling workflow continuation:',
                                error,
                            );
                        },
                    );
                }

                // Slack expects a 200 response within 3 seconds
                return reply.code(200).send({ ok: true });
            } catch (error) {
                console.error('Error processing Slack interaction:', error);
                return reply.code(200).send({
                    text: 'Error processing interaction',
                });
            }
        },
    );

    /**
     * Slack Slash Commands webhook endpoint
     * Receives slash commands like /workflow run my-workflow
     *
     * Note: This endpoint must be publicly accessible and registered as the
     * "Request URL" for your slash command in Slack app settings.
     */
    server.post(
        '/webhook/slack/commands',
        {
            schema: {
                description: 'Slack slash commands webhook',
                tags: ['Webhook'],
            },
            // Skip authentication - Slack calls this endpoint directly
            config: {
                skipAuth: true,
            },
        },
        async (request, reply) => {
            try {
                const signingSecret = server.config.slack.signingSecret;
                if (signingSecret) {
                    if (!verifySlackSignature(request, signingSecret)) {
                        console.error(
                            'Invalid Slack signature for slash command',
                        );
                        return reply
                            .code(401)
                            .send({ error: 'Invalid signature' });
                    }
                }

                const body = request.body as SlackSlashCommandPayload;

                console.log(
                    `📥 Received slash command via HTTP: ${body.command} ${body.text}`,
                );

                // Parse and execute the command
                const parsedCommand = parseCommand(body.text);
                const result = await executeCommand(parsedCommand, body, {
                    db: server.db,
                    runnerRegistry: server.runnerRegistry,
                    logService: server.logService,
                    sandboxConfig: server.config.sandbox,
                    secretBackend: server.config.secretBackend,
                });

                // Return immediate response
                // Further async updates will be sent via response_url
                return reply.code(200).send({
                    response_type: 'ephemeral',
                    text: result.message,
                    blocks: result.blocks,
                });
            } catch (error) {
                console.error('Error processing Slack slash command:', error);
                return reply.code(200).send({
                    response_type: 'ephemeral',
                    text: '❌ Error processing command. Please try again.',
                });
            }
        },
    );
}

/**
 * Updates a Slack message using the response_url
 */
async function updateSlackMessage(
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
 * Handles workflow continuation after an interrupt is resumed
 * This runs asynchronously after responding to Slack
 */
async function handleWorkflowContinuation(
    server: FastifyInstance,
    runner: ReturnType<NonNullable<typeof server.runnerRegistry>['get']>,
    interrupt: { runId: string; workflowId: string },
): Promise<void> {
    if (!runner) return;

    const nextResult = await runner.waitForNextEvent();

    if (nextResult.status === 'interrupted' && nextResult.pendingInterrupt) {
        // Workflow hit another interrupt - save it to database
        await server.db.workflowInterrupt.create({
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
        await server.db.workflowRun.update({
            where: { id: interrupt.runId },
            data: { status: 'Interrupted' },
        });
    } else {
        // Workflow completed or failed
        await server.db.workflowRun.update({
            where: { id: interrupt.runId },
            data: {
                status:
                    nextResult.status === 'completed' ? 'Completed' : 'Failed',
                completedAt: new Date(),
            },
        });

        // Clean up runner from registry
        server.runnerRegistry?.delete(interrupt.runId);
    }
}
