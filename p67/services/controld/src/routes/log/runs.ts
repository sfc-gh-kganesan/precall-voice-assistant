import {
    ErrorResponseSchema,
    RunListQuerySchema,
    RunListResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerRunListRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/runs',
        {
            schema: {
                description: 'List runs for a workflow',
                tags: ['Log'],
                querystring: RunListQuerySchema,
                response: {
                    200: RunListResponseSchema,
                    400: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { workflowId, limit, offset } = request.query;

                const runs = await fastify.logService.findRunsByWorkflowAndUser(
                    workflowId,
                    request.user.id,
                    { limit, offset },
                );

                const total =
                    await fastify.logService.countRunsByWorkflowAndUser(
                        workflowId,
                        request.user.id,
                    );

                type ApiRunStatus =
                    | 'running'
                    | 'completed'
                    | 'failed'
                    | 'interrupted';
                const statusMap: Record<string, ApiRunStatus> = {
                    Running: 'running',
                    Completed: 'completed',
                    Interrupted: 'interrupted',
                    Failed: 'failed',
                };

                return reply.code(200).send({
                    runs: runs.map((run) => ({
                        id: run.id,
                        workflowId: run.workflowId,
                        status: statusMap[run.status] ?? ('running' as const),
                        startedAt: run.startedAt.toISOString(),
                        completedAt: run.completedAt?.toISOString() ?? null,
                        exitCode: run.exitCode,
                        logCount: run._count.logs,
                    })),
                    total,
                });
            } catch (error) {
                console.error('Error listing runs:', error);
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
