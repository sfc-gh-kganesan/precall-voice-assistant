import { Hono } from 'hono';
import health from './health.js';
import workflow from './workflow.js';

const api = new Hono();

api.route('/health', health);
api.route('/workflow', workflow);

export default api;
