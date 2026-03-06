import { existsSync } from 'node:fs';
import { formatDateISO } from '@controld/lib/fmt.js';
import { Runner } from '@controld/lib/runner.js';
import {
    ErrorResponseSchema,
    WorkflowListResponseSchema,
    WorkflowRunAcceptedSchema,
    WorkflowRunBodySchema,
    WorkflowRunResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';

const WorkflowNameParamsSchema = z.object({
    name: z
        .string()
        .min(1, 'Name cannot be empty')
        .max(128, 'Name too long')
        .regex(
            /^[a-zA-Z0-9_-]+$/,
            'Name may only contain letters, numbers, hyphens, and underscores',
        ),
});

export function registerByNameRoutes(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    // Run workflow by name (uses latest version)
    fastify.post(
        '/name/:name/run',
        {
            schema: {
                description: 'Run the latest version of a workflow by name',
                tags: ['Workflow'],
                params: WorkflowNameParamsSchema,
                body: WorkflowRunBodySchema,
                response: {
                    200: WorkflowRunResponseSchema,
                    202: WorkflowRunAcceptedSchema,
                    400: ErrorResponseSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { name } = request.params as { name: string };
                const params =
                    (request.body as { params?: Record<string, string> })
                        ?.params ?? {};
                const syncMode =
                    (request.query as { sync?: string })?.sync === 'true';

                const workflow = await fastify.workflowService.findLatestByName(
                    name,
                    request.user.id,
                );

                if (!workflow) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `No workflow found with name "${name}"`,
                    });
                }

                if (!existsSync(workflow.storagePath)) {
                    return reply.code(400).send({
                        error: 'Invalid request',
                        message: `Workflow ${workflow.id} does not exist on disk`,
                    });
                }

                const runnerInstance = new Runner(
                    workflow.storagePath,
                    fastify.db,
                    request.user.id,
                    fastify.logService,
                    params,
                    fastify.config.sandbox,
                );

                // Create the run record before starting so we can return the runId
                const runId = await runnerInstance.init();

                // Register runner in registry for potential resume operations
                fastify.runnerRegistry.set(runId, runnerInstance);

                // Synchronous mode: wait for the result (used by subworkflow calls)
                if (syncMode) {
                    const result = await runnerInstance.start();
                    fastify.runnerRegistry.delete(runId);
                    return reply.code(200).send({
                        exitCode: result.exitCode,
                        stdout: result.stdout,
                        stderr: result.stderr,
                        log: result.log,
                        success: result.exitCode === 0,
                        errors: result.errors,
                        status: result.status,
                        runId: result.runId,
                        result: result.result,
                        pendingInterrupt: result.pendingInterrupt,
                    });
                }

                // Async mode (default): fire off execution in the background
                runnerInstance
                    .start()
                    .then(async (result) => {
                        // Handle interrupted workflows
                        if (
                            result.status === 'interrupted' &&
                            result.pendingInterrupt
                        ) {
                            await fastify.db.workflowInterrupt.create({
                                data: {
                                    id: result.pendingInterrupt.interruptId,
                                    runId: result.runId,
                                    workflowId: workflow.id,
                                    payload: result.pendingInterrupt
                                        .value as object,
                                    nodeId: result.pendingInterrupt.nodeId,
                                    status: 'Pending',
                                },
                            });

                            await fastify.db.workflowRun.update({
                                where: { id: result.runId },
                                data: { status: 'Interrupted' },
                            });

                            // Wait for eventual completion after resume
                            runnerInstance
                                .waitForCompletion()
                                .then(async (finalResult) => {
                                    fastify.runnerRegistry.delete(
                                        finalResult.runId,
                                    );
                                    await fastify.db.workflowRun.update({
                                        where: { id: finalResult.runId },
                                        data: {
                                            status:
                                                finalResult.status ===
                                                'completed'
                                                    ? 'Completed'
                                                    : 'Failed',
                                            completedAt: new Date(),
                                        },
                                    });
                                })
                                .catch((err) => {
                                    console.error(
                                        'Error waiting for workflow completion:',
                                        err,
                                    );
                                    fastify.runnerRegistry.delete(result.runId);
                                });
                        } else {
                            // Workflow completed or failed — clean up
                            fastify.runnerRegistry.delete(result.runId);
                        }
                    })
                    .catch((err) => {
                        console.error('Background workflow run failed:', err);
                        fastify.runnerRegistry.delete(runId);
                    });

                // Return immediately with the run ID
                return reply.code(202).send({
                    runId,
                    status: 'running',
                });
            } catch (error) {
                console.error('Error running workflow by name:', error);
                return reply.code(500).send({
                    error: 'Internal server error',
                    message:
                        error instanceof Error
                            ? error.message
                            : 'Unknown error',
                });
            }
        },
    );

    // List all versions of a workflow by name
    fastify.get(
        '/name/:name/versions',
        {
            schema: {
                description: 'List all versions of a workflow by name',
                tags: ['Workflow'],
                params: WorkflowNameParamsSchema,
                response: {
                    200: WorkflowListResponseSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { name } = request.params as { name: string };

                const workflows =
                    await fastify.workflowService.findAllVersionsByName(
                        name,
                        request.user.id,
                    );

                if (workflows.length === 0) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `No workflow found with name "${name}"`,
                    });
                }

                return reply.code(200).send({
                    workflows: workflows.map((w) => ({
                        workflowId: w.id,
                        name: w.name,
                        createdAt: formatDateISO(w.createdAt),
                        updatedAt: formatDateISO(w.updatedAt),
                        owner: w.owner.snowflakeUser,
                        visibility: w.visibility,
                    })),
                });
            } catch (error) {
                console.error('Error listing workflow versions:', error);
                return reply.code(500).send({
                    error: 'Internal server error',
                    message:
                        error instanceof Error
                            ? error.message
                            : 'Unknown error',
                });
            }
        },
    );
}
