import type { FastifyInstance } from 'fastify';
import { registerDeleteRoute } from './delete.js';
import { registerListRoute } from './list.js';
import { registerSaveRoute } from './save.js';

const secretRoutes = async (server: FastifyInstance) => {
    registerSaveRoute(server);
    registerListRoute(server);
    registerDeleteRoute(server);
};

export default secretRoutes;
