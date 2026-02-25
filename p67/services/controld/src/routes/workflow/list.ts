import { formatDateISO } from '@controld/lib/fmt.js';
import {
    ErrorResponseSchema,
    WorkflowListResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerListRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/list',
        {
            schema: {
                description: 'List all workflows',
                tags: ['Workflow'],
                response: {
                    200: WorkflowListResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (req, reply) => {
            try {
                const workflows =
                    await fastify.workflowService.findAllRunnableWorkflowsByUser(
                        req.user.id,
                    );
                return reply.code(200).send({
                    workflows: workflows.map((w) => {
                        return {
                            workflowId: w.id,
                            name: w.name,
                            createdAt: formatDateISO(w.createdAt),
                            updatedAt: formatDateISO(w.updatedAt),
                            owner: w.owner.snowflakeUser,
                            visibility: w.visibility,
                        };
                    }),
                });
            } catch (error) {
                console.error('Error listing workflows:', error);
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
