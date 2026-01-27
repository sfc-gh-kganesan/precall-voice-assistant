import { decrypt } from '@controld/lib/crypto.js';
import { formatDateISO } from '@controld/lib/fmt.js';
import {
    ErrorResponseSchema,
    SecretGetParamsSchema,
    SecretGetResponseSchema,
} from '@controld/schema.js';
import type { FastifyInstance } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';

export function registerGetRoute(server: FastifyInstance) {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/:name',
        {
            schema: {
                description: 'Get a secret by name (decrypted)',
                tags: ['Secret'],
                params: SecretGetParamsSchema,
                response: {
                    200: SecretGetResponseSchema,
                    404: ErrorResponseSchema,
                    500: ErrorResponseSchema,
                },
            },
        },
        async (request, reply) => {
            try {
                const { name } = request.params;
                const secret = await fastify.secretService.findByName(
                    request.user.id,
                    name,
                );

                if (!secret) {
                    return reply.code(404).send({
                        error: 'Not found',
                        message: `Secret '${name}' not found`,
                    });
                }

                // Decrypt the secret value
                const decryptedValue = decrypt(secret.secret);

                return reply.code(200).send({
                    name: secret.name,
                    value: decryptedValue,
                    createdAt: formatDateISO(secret.createdAt),
                    updatedAt: formatDateISO(secret.updatedAt),
                });
            } catch (error) {
                console.error('Error getting secret:', error);
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
