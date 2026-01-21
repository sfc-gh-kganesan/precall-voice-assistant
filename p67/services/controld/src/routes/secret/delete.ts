import {
    ErrorResponseSchema,
    SecretDeleteParamsSchema,
    SecretDeleteResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerDeleteRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.delete(
        '/:name',
        {
            schema: {
                description: 'Delete a secret by name',
                tags: ['Secret'],
                params: SecretDeleteParamsSchema,
                response: {
                    200: SecretDeleteResponseSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { name } = request.params;

                const deleted = await fastify.secretService.delete(
                    request.user.id,
                    name,
                );

                if (!deleted) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Secret '${name}' not found`,
                    });
                }

                return reply.code(200).send({ deleted: true, name });
            } catch (error) {
                console.error('Error deleting secret:', error);
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
