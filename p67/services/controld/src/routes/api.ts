import { FastifyPluginAsync } from 'fastify';
import health from './health.js';

const api: FastifyPluginAsync = async (fastify) => {
  await fastify.register(health, { prefix: '/health' });
};

export default api;
