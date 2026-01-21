import type { FastifyInstance } from 'fastify';
import { registerLogListRoute } from './list.js';
import { registerRunListRoute } from './runs.js';

const logRoutes = async (server: FastifyInstance) => {
    registerLogListRoute(server);
    registerRunListRoute(server);
};

export default logRoutes;
