import { existsSync } from 'node:fs';
import { Runner } from '@controld/lib/runner.js';
import {
    ErrorResponseSchema,
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
                );
                const { stdout, stderr, exitCode, errors, log } =
                    await runnerInstance.start();

                return reply.code(200).send({
                    exitCode,
                    stdout,
                    stderr,
                    errors,
                    log,
                    success: exitCode === 0,
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
