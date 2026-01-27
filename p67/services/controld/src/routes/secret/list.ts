import { formatDateISO } from '@controld/lib/fmt.js';
import {
    ErrorResponseSchema,
    SecretListQuerySchema,
    SecretListResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerListRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/list',
        {
            schema: {
                description: 'List all secrets for the authenticated user',
                tags: ['Secret'],
                querystring: SecretListQuerySchema,
                response: {
                    200: SecretListResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { type } = request.query;
                const secrets = await fastify.secretService.list(
                    request.user.id,
                    type,
                );

                return reply.code(200).send({
                    secrets: secrets.map((s) => ({
                        name: s.name,
                        type: s.type,
                        createdAt: formatDateISO(s.createdAt),
                        updatedAt: formatDateISO(s.updatedAt),
                    })),
                });
            } catch (error) {
                console.error('Error listing secrets:', error);
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
