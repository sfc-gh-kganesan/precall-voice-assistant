import { existsSync } from 'node:fs';
import { Runner } from '@controld/lib/runner.js';
import {
    ErrorResponseSchema,
    WorkflowRunAcceptedSchema,
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
                    202: WorkflowRunAcceptedSchema,
                    400: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { workflowId } = request.params as { workflowId: string };
                const body = request.body as WorkflowRunBody;
                const params = body?.params ?? {};
                const syncMode =
                    (request.query as { sync?: string })?.sync === 'true';
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
                                    workflowId: workflowId,
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
