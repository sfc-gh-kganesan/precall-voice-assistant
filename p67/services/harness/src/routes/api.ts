import { OpenAPIHono } from '@hono/zod-openapi';
import health from './health.js';
import workflow from './workflow.js';

const api = new OpenAPIHono();

api.route('/health', health);
api.route('/workflow', workflow);

export default api;
