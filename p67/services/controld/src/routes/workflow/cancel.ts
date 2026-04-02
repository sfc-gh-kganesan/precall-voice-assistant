import {
    ErrorResponseSchema,
    WorkflowRunCancelParamsSchema,
    WorkflowRunCancelResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerCancelRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.post(
        '/runs/:runId/cancel',
        {
            schema: {
                description: 'Cancel a running or interrupted workflow run',
                tags: ['Workflow'],
                params: WorkflowRunCancelParamsSchema,
                response: {
                    200: WorkflowRunCancelResponseSchema,
                    400: ErrorResponseSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { runId } = request.params;

                const run = await fastify.db.workflowRun.findFirst({
                    where: { id: runId },
                    include: {
                        workflow: {
                            select: { ownerId: true },
                        },
                    },
                });

                if (!run) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Run ${runId} not found`,
                    });
                }

                // Access check: user owns the run or owns the workflow
                if (
                    run.userId !== request.user.id &&
                    run.workflow.ownerId !== request.user.id
                ) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Run ${runId} not found or you do not have access`,
                    });
                }

                // Only allow cancelling runs in Running or Interrupted state
                if (run.status !== 'Running' && run.status !== 'Interrupted') {
                    return reply.code(400).send({
                        error: 'Bad request',
                        message: `Run ${runId} cannot be cancelled (current status: ${run.status})`,
                    });
                }

                // Update DB to Cancelled FIRST — wins race with background thread
                await fastify.db.workflowRun.update({
                    where: { id: runId },
                    data: {
                        status: 'Cancelled',
                        completedAt: new Date(),
                    },
                });

                // If an active runner exists, cancel it and remove from registry
                const runner = fastify.runnerRegistry.get(runId);
                if (runner) {
                    await runner.cancel();
                    fastify.runnerRegistry.delete(runId);
                }

                return reply.code(200).send({ cancelled: true, runId });
            } catch (error) {
                console.error('Error cancelling run:', error);
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
