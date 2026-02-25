import { existsSync } from 'node:fs';
import { Runner } from '@controld/lib/runner.js';
import {
    ErrorResponseSchema,
    type WorkflowRunBody,
    WorkflowRunBodySchema,
    WorkflowRunParamsSchema,
    WorkflowRunResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerRunRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.post(
        '/:workflowId/run',
        {
            schema: {
                description: 'Run a workflow',
                tags: ['Workflow'],
                params: WorkflowRunParamsSchema,
                body: WorkflowRunBodySchema,
                response: {
                    200: WorkflowRunResponseSchema,
                    400: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { workflowId } = request.params as { workflowId: string };
                const body = request.body as WorkflowRunBody;
                const params = body?.params;
                const workflow =
                    await fastify.workflowService.findRunnableWorkflowByUser(
                        workflowId,
                        request.user.id,
                    );

                if (!workflow) {
                    return reply.code(400).send({
                        error: 'Invalid request',
                        message: `Workflow ${workflowId} either does not exist or you do not have permission to access it`,
                    });
                }

                if (!existsSync(workflow.storagePath)) {
                    return reply.code(400).send({
                        error: 'Invalid request',
                        message: `Workflow ${workflowId} does not exist on disk at the expected path ${workflow.storagePath}`,
                    });
                }

                const runnerInstance = new Runner(
                    workflow.storagePath,
                    fastify.db,
                    request.user.id,
                    fastify.logService,
                    params,
                );
                const result = await runnerInstance.start();

                // Register runner in registry for potential resume operations
                fastify.runnerRegistry.set(result.runId, runnerInstance);

                // Handle interrupted workflows
                if (
                    result.status === 'interrupted' &&
                    result.pendingInterrupt
                ) {
                    // Create interrupt record in database
                    await fastify.db.workflowInterrupt.create({
                        data: {
                            id: result.pendingInterrupt.interruptId,
                            runId: result.runId,
                            workflowId: workflowId,
                            payload: result.pendingInterrupt.value as object,
                            nodeId: result.pendingInterrupt.nodeId,
                            status: 'Pending',
                        },
                    });

                    // Update run status to Interrupted
                    await fastify.db.workflowRun.update({
                        where: { id: result.runId },
                        data: { status: 'Interrupted' },
                    });

                    // Set up cleanup when workflow eventually completes
                    runnerInstance
                        .waitForCompletion()
                        .then(async (finalResult) => {
                            // Clean up runner from registry
                            fastify.runnerRegistry.delete(finalResult.runId);

                            // Update run status based on final result
                            await fastify.db.workflowRun.update({
                                where: { id: finalResult.runId },
                                data: {
                                    status:
                                        finalResult.status === 'completed'
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
                    // Workflow completed or failed - clean up immediately
                    fastify.runnerRegistry.delete(result.runId);
                }

                return reply.code(200).send({
                    exitCode: result.exitCode,
                    stdout: result.stdout,
                    stderr: result.stderr,
                    errors: result.errors,
                    log: result.log,
                    success: result.exitCode === 0,
                    status: result.status,
                    pendingInterrupt: result.pendingInterrupt,
                    runId: result.runId,
                });
            } catch (error) {
                console.error('Error running workflow:', error);
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
