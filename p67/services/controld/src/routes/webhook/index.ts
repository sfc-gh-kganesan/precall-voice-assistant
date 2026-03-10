import type { FastifyPluginAsync } from 'fastify';
import { registerSlackWebhookRoutes } from './slack.js';
import { registerSnowflakeWebhookRoutes } from './snowflake.js';

const webhook: FastifyPluginAsync = async (fastify) => {
    registerSlackWebhookRoutes(fastify);
    registerSnowflakeWebhookRoutes(fastify);
};

export default webhook;
