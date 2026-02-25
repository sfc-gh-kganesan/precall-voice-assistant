import type { FastifyInstance } from 'fastify';
import { registerCreateRoute } from './create.js';
import { registerInterruptRoutes } from './interrupt.js';
import { registerListRoute } from './list.js';
import { registerManifestRoute } from './manifest.js';
import { registerRunRoute } from './run.js';

const workflowRoutes = async (server: FastifyInstance) => {
    console.log('[WorkflowRoutes] Registering create route...');
    registerCreateRoute(server);
    console.log('[WorkflowRoutes] Registering list route...');
    registerListRoute(server);
    console.log('[WorkflowRoutes] Registering manifest route...');
    registerManifestRoute(server);
    console.log('[WorkflowRoutes] Registering run route...');
    registerRunRoute(server);
    console.log('[WorkflowRoutes] Registering interrupt routes...');
    try {
        registerInterruptRoutes(server);
        console.log(
            '[WorkflowRoutes] Interrupt routes registered successfully',
        );
    } catch (error) {
        console.error(
            '[WorkflowRoutes] Failed to register interrupt routes:',
            error,
        );
    }
};

export default workflowRoutes;
