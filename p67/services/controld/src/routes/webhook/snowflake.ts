import { existsSync } from 'node:fs';
import { Runner } from '@controld/lib/runner.js';
import type { FastifyInstance } from 'fastify';

const WEBHOOK_SYSTEM_USER = '__webhook__';

/**
 * Snowflake External Function webhook endpoint.
 *
 * Snowflake external functions use a batch-row protocol:
 *   Request:  { "data": [[0, <arg1>], [1, <arg1>], ...] }
 *   Response: { "data": [[0, <result>], [1, <result>], ...] }
 *
 * This route accepts that format, triggers a workflow run for each row,
 * and returns results keyed by row index.
 */
export function registerSnowflakeWebhookRoutes(server: FastifyInstance) {
    server.post(
        '/webhook/snowflake/:workflowName',
        {
            schema: {
                description:
                    'Snowflake external function webhook — triggers a workflow by name',
                tags: ['Webhook'],
            },
            config: {
                skipAuth: true,
            },
        },
        async (request, reply) => {
            try {
                // Auth: When running on SPCS, this endpoint is protected by:
                //   1. SPCS ingress OAuth (public endpoint requires Snowflake login)
                //   2. Service role grants (service functions require webhook_caller role)
                // For external callers, optionally validate a bearer token.
                const webhookSecret = process.env.SNOWFLAKE_WEBHOOK_SECRET;
                const authHeader = request.headers.authorization;
                if (webhookSecret && authHeader) {
                    if (authHeader !== `Bearer ${webhookSecret}`) {
                        return reply.code(401).send({
                            data: [[0, { error: 'Unauthorized' }]],
                        });
                    }
                }

                const { workflowName } = request.params as {
                    workflowName: string;
                };

                // Parse Snowflake batch format
                const body = request.body as {
                    data?: Array<[number, ...unknown[]]>;
                };
                if (!body?.data || !Array.isArray(body.data)) {
                    return reply.code(400).send({
                        data: [
                            [
                                0,
                                {
                                    error: 'Invalid request — expected Snowflake external function format {"data": [[row_index, ...]]}',
                                },
                            ],
                        ],
                    });
                }

                // Get or create the webhook system user
                let webhookUser = await server.db.user.findUnique({
                    where: { snowflakeUser: WEBHOOK_SYSTEM_USER },
                });
                if (!webhookUser) {
                    webhookUser = await server.db.user.create({
                        data: { snowflakeUser: WEBHOOK_SYSTEM_USER },
                    });
                    request.log.info(
                        `Created webhook system user with id ${webhookUser.id}`,
                    );
                }

                // Look up the workflow (only Public workflows are accessible)
                const workflow = await server.workflowService.findLatestByName(
                    workflowName,
                    webhookUser.id,
                );

                if (!workflow) {
                    return reply.code(404).send({
                        data: body.data.map(([rowIndex]) => [
                            rowIndex,
                            {
                                error: `No public workflow found with name "${workflowName}"`,
                            },
                        ]),
                    });
                }

                if (!existsSync(workflow.storagePath)) {
                    return reply.code(400).send({
                        data: body.data.map(([rowIndex]) => [
                            rowIndex,
                            {
                                error: `Workflow ${workflow.id} does not exist on disk`,
                            },
                        ]),
                    });
                }

                const asyncMode =
                    (request.query as { mode?: string })?.mode === 'async';

                // Process each row
                const results: Array<[number, unknown]> = [];

                for (const row of body.data) {
                    const rowIndex = row[0];
                    const variantArg = row[1];

                    // Convert the VARIANT object fields to string params
                    const params: Record<string, string> = {};
                    if (
                        variantArg &&
                        typeof variantArg === 'object' &&
                        !Array.isArray(variantArg)
                    ) {
                        for (const [key, value] of Object.entries(
                            variantArg as Record<string, unknown>,
                        )) {
                            params[key] =
                                value === null || value === undefined
                                    ? ''
                                    : String(value);
                        }
                    }

                    try {
                        const runnerInstance = new Runner(
                            workflow.storagePath,
                            server.db,
                            webhookUser.id,
                            server.logService,
                            params,
                            server.config.sandbox,
                            server.config.secretBackend,
                        );

                        const runId = await runnerInstance.init();
                        server.runnerRegistry.set(runId, runnerInstance);

                        if (asyncMode) {
                            // Async: fire-and-forget, return runId immediately
                            runnerInstance
                                .start()
                                .then(async (result) => {
                                    if (
                                        result.status === 'interrupted' &&
                                        result.pendingInterrupt
                                    ) {
                                        await server.db.workflowInterrupt.create(
                                            {
                                                data: {
                                                    id: result.pendingInterrupt
                                                        .interruptId,
                                                    runId: result.runId,
                                                    workflowId: workflow.id,
                                                    payload: result
                                                        .pendingInterrupt
                                                        .value as object,
                                                    nodeId: result
                                                        .pendingInterrupt
                                                        .nodeId,
                                                    status: 'Pending',
                                                },
                                            },
                                        );
                                        await server.db.workflowRun.update({
                                            where: { id: result.runId },
                                            data: { status: 'Interrupted' },
                                        });
                                    } else {
                                        server.runnerRegistry.delete(
                                            result.runId,
                                        );
                                    }
                                })
                                .catch((err) => {
                                    console.error(
                                        `Snowflake webhook workflow run failed (row ${rowIndex}):`,
                                        err,
                                    );
                                    server.runnerRegistry.delete(runId);
                                });

                            results.push([
                                rowIndex,
                                { runId, status: 'running' },
                            ]);
                        } else {
                            // Sync (default): await result and return it
                            const result = await runnerInstance.start();
                            server.runnerRegistry.delete(runId);
                            results.push([
                                rowIndex,
                                {
                                    runId,
                                    status: result.status,
                                    exitCode: result.exitCode,
                                    result: result.result ?? null,
                                    errors:
                                        result.errors &&
                                        result.errors.length > 0
                                            ? result.errors
                                            : undefined,
                                },
                            ]);
                        }
                    } catch (err) {
                        request.log.error(
                            err,
                            `Failed to start workflow for row ${rowIndex}`,
                        );
                        results.push([
                            rowIndex,
                            {
                                error:
                                    err instanceof Error
                                        ? err.message
                                        : 'Unknown error',
                            },
                        ]);
                    }
                }

                return reply.code(200).send({ data: results });
            } catch (error) {
                console.error('Error processing Snowflake webhook:', error);
                return reply.code(500).send({
                    data: [
                        [
                            0,
                            {
                                error:
                                    error instanceof Error
                                        ? error.message
                                        : 'Internal server error',
                            },
                        ],
                    ],
                });
            }
        },
    );
}
