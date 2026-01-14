import type { FastifyInstance } from 'fastify';
import { registerCreateRoute } from './create.js';
import { registerListRoute } from './list.js';
import { registerRunRoute } from './run.js';

const workflowRoutes = async (server: FastifyInstance) => {
    registerCreateRoute(server);
    registerListRoute(server);
    registerRunRoute(server);
};

export default workflowRoutes;
