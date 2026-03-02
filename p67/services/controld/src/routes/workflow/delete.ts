import { WorkflowLockedError } from '@controld/lib/WorkflowService.js';
import {
    ErrorResponseSchema,
    WorkflowDeleteParamsSchema,
    WorkflowDeleteResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerDeleteRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.delete(
        '/:workflowId',
        {
            schema: {
                description: 'Delete a workflow by ID',
                tags: ['Workflow'],
                params: WorkflowDeleteParamsSchema,
                response: {
                    200: WorkflowDeleteResponseSchema,
                    404: ErrorResponseSchema,
                    409: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { workflowId } = request.params;

                const deleted = await fastify.workflowService.delete(
                    workflowId,
                    request.user.id,
                );

                if (!deleted) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Workflow '${workflowId}' not found or not owned by you`,
                    });
                }

                return reply.code(200).send({ deleted: true, workflowId });
            } catch (error) {
                if (error instanceof WorkflowLockedError) {
                    return reply.code(409).send({
                        error: 'Conflict',
                        message: error.message,
                    });
                }
                console.error('Error deleting workflow:', error);
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
