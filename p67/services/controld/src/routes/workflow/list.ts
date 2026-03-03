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

                // Compute version counts for named workflows
                const versionCounts = new Map<string, number>();
                for (const w of workflows) {
                    if (w.name) {
                        const key = `${w.ownerId}:${w.name}`;
                        versionCounts.set(
                            key,
                            (versionCounts.get(key) ?? 0) + 1,
                        );
                    }
                }

                return reply.code(200).send({
                    workflows: workflows.map((w) => {
                        const versionCount = w.name
                            ? versionCounts.get(`${w.ownerId}:${w.name}`)
                            : undefined;
                        return {
                            workflowId: w.id,
                            name: w.name,
                            createdAt: formatDateISO(w.createdAt),
                            updatedAt: formatDateISO(w.updatedAt),
                            owner: w.owner.snowflakeUser,
                            visibility: w.visibility,
                            versionCount,
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
