import { FastifyPluginAsync } from 'fastify';
import health from '@controld/routes/health.js';
import workflow from '@controld/routes/workflow.js';
import auth from '@controld/routes/auth.js';
import whoami from '@controld/routes/whoami.js';

const api: FastifyPluginAsync = async (fastify) => {
  await fastify.register(health, { prefix: '/health' });
  await fastify.register(workflow, { prefix: '/workflow' });
  await fastify.register(auth, { prefix: '/auth' });
  await fastify.register(whoami, { prefix: '/whoami' });
};

export default api;
