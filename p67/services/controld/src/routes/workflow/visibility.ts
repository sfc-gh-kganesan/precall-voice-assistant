import {
    ErrorResponseSchema,
    WorkflowVisibilityBodySchema,
    WorkflowVisibilityParamsSchema,
    WorkflowVisibilityResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerVisibilityRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.patch(
        '/:workflowId/visibility',
        {
            schema: {
                description: 'Update workflow visibility (Private or Public)',
                tags: ['Workflow'],
                params: WorkflowVisibilityParamsSchema,
                body: WorkflowVisibilityBodySchema,
                response: {
                    200: WorkflowVisibilityResponseSchema,
                    400: ErrorResponseSchema,
                    403: ErrorResponseSchema,
                    404: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            const { workflowId } = request.params as { workflowId: string };
            const { visibility } = request.body as {
                visibility: 'Private' | 'Public';
            };

            const workflow = await fastify.workflowService.findById(workflowId);

            if (!workflow) {
                return reply.code(404).send({
                    error: 'Not found',
                    message: `Workflow ${workflowId} not found`,
                });
            }

            if (
                !fastify.workflowService.rbacUserCanUpdate(
                    request.user.id,
                    workflow,
                )
            ) {
                return reply.code(403).send({
                    error: 'Forbidden',
                    message: 'Only the workflow owner can change visibility',
                });
            }

            const updated = await fastify.workflowService.setVisibility(
                workflowId,
                visibility,
            );

            return reply.code(200).send({
                workflowId: updated.id,
                visibility: updated.visibility,
            });
        },
    );
}
