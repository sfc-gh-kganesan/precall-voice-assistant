import type { FastifyPluginAsync } from 'fastify';
import { registerSlackWebhookRoutes } from './slack.js';

const webhook: FastifyPluginAsync = async (fastify) => {
    registerSlackWebhookRoutes(fastify);
};

export default webhook;
