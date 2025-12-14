import { FastifyPluginAsync } from 'fastify';
import health from './health.js';
import workflow from './workflow.js';
import auth from './auth.js';

const api: FastifyPluginAsync = async (fastify) => {
  await fastify.register(health, { prefix: '/health' });
  await fastify.register(workflow, { prefix: '/workflow' });
  await fastify.register(auth, { prefix: '/auth' });
};

export default api;
