import { HealthResponseSchema } from '@controld/schema.js';
import type { FastifyPluginAsync } from 'fastify';

const health: FastifyPluginAsync = async (fastify) => {
    fastify.get(
        '/',
        {
            schema: {
                tags: ['Health'],
                summary: 'Health check',
                description: 'Returns the health status of the service',
                response: {
                    200: HealthResponseSchema,
                },
            },
        },
        async (request) => {
            return {
                status: 'ok',
                timestamp: new Date().toISOString(),
                localStoragePath: request.server.config.localStoragePath,
            };
        },
    );
};

export default health;
