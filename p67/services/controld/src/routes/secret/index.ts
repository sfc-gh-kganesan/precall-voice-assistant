import type { FastifyInstance } from 'fastify';
import { registerDeleteRoute } from './delete.js';
import { registerGetRoute } from './get.js';
import { registerListRoute } from './list.js';
import { registerOAuthRefreshRoute } from './oauth-refresh.js';
import { registerSaveRoute } from './save.js';

const secretRoutes = async (server: FastifyInstance) => {
    registerSaveRoute(server);
    registerListRoute(server);
    registerDeleteRoute(server);
    registerGetRoute(server);
    registerOAuthRefreshRoute(server);
};

export default secretRoutes;
