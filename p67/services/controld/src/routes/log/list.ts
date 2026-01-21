import {
    ErrorResponseSchema,
    LogListQuerySchema,
    LogListResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerLogListRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/list',
        {
            schema: {
                description: 'List logs for workflows accessible by the user',
                tags: ['Log'],
                querystring: LogListQuerySchema,
                response: {
                    200: LogListResponseSchema,
                    400: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { workflowId, runId, source, limit, offset } =
                    request.query;

                const logs = await fastify.logService.findLogsByUser(
                    request.user.id,
                    {
                        workflowId,
                        runId,
                        source,
                        limit,
                        offset,
                    },
                );

                const total = await fastify.logService.countLogsByUser(
                    request.user.id,
                    {
                        workflowId,
                        runId,
                        source,
                    },
                );

                return reply.code(200).send({
                    logs: logs.map((log) => ({
                        id: log.id,
                        runId: log.runId,
                        workflowId: log.workflowId,
                        source: log.source,
                        message: log.message,
                        attributes: log.attributes as Record<string, unknown>,
                        timestamp: log.timestamp.toISOString(),
                    })),
                    total,
                });
            } catch (error) {
                console.error('Error listing logs:', error);
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
