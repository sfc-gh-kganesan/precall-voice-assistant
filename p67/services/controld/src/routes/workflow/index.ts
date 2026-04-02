import type { FastifyInstance } from 'fastify';
import { registerByNameRoutes } from './byName.js';
import { registerCancelRoute } from './cancel.js';
import { registerCreateRoute } from './create.js';
import { registerDeleteRoute } from './delete.js';
import { registerGraphRoute } from './graph.js';
import { registerInterruptRoutes } from './interrupt.js';
import { registerListRoute } from './list.js';
import { registerManifestRoute } from './manifest.js';
import { registerRunRoute } from './run.js';
import { registerStatusRoute } from './status.js';
import { registerVisibilityRoute } from './visibility.js';

const workflowRoutes = async (server: FastifyInstance) => {
    console.log('[WorkflowRoutes] Registering create route...');
    registerCreateRoute(server);
    console.log('[WorkflowRoutes] Registering list route...');
    registerListRoute(server);
    console.log('[WorkflowRoutes] Registering manifest route...');
    registerManifestRoute(server);
    console.log('[WorkflowRoutes] Registering graph route...');
    registerGraphRoute(server);
    console.log('[WorkflowRoutes] Registering run route...');
    registerRunRoute(server);
    console.log('[WorkflowRoutes] Registering visibility route...');
    registerVisibilityRoute(server);
    console.log('[WorkflowRoutes] Registering delete route...');
    registerDeleteRoute(server);
    console.log('[WorkflowRoutes] Registering by-name routes...');
    registerByNameRoutes(server);
    console.log('[WorkflowRoutes] Registering status route...');
    registerStatusRoute(server);
    console.log('[WorkflowRoutes] Registering cancel route...');
    registerCancelRoute(server);
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
