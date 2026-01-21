import auth from '@controld/routes/auth.js';
import health from '@controld/routes/health.js';
import secret from '@controld/routes/secret/index.js';
import whoami from '@controld/routes/whoami.js';
import workflow from '@controld/routes/workflow/index.js';
import type { FastifyPluginAsync } from 'fastify';

const api: FastifyPluginAsync = async (fastify) => {
    await fastify.register(health, { prefix: '/health' });
    await fastify.register(workflow, { prefix: '/workflow' });
    await fastify.register(secret, { prefix: '/secret' });
    await fastify.register(auth, { prefix: '/auth' });
    await fastify.register(whoami, { prefix: '/whoami' });
};

export default api;
