import {
    ErrorResponseSchema,
    SecretSaveBodySchema,
    SecretSaveResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerSaveRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.post(
        '/save',
        {
            schema: {
                description: 'Save or update a secret',
                tags: ['Secret'],
                body: SecretSaveBodySchema,
                response: {
                    200: SecretSaveResponseSchema,
                    400: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { name, secret, type } = request.body;

                const result = await fastify.secretService.save(
                    request.user.id,
                    name,
                    secret,
                    type,
                );

                return reply.code(200).send(result);
            } catch (error) {
                console.error('Error saving secret:', error);
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
