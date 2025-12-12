import { createRoute, OpenAPIHono } from '@hono/zod-openapi';
import type { Env } from '../middleware/env.js';
import { HealthResponseSchema } from '../schema.js';

const health = new OpenAPIHono<Env>();

const healthRoute = createRoute({
  method: 'get',
  path: '/',
  tags: ['Health'],
  summary: 'Health check',
  description: 'Returns the health status of the service',
  responses: {
    200: {
      description: 'Service is healthy',
      content: {
        'application/json': {
          schema: HealthResponseSchema,
        },
      },
    },
  },
});

health.openapi(healthRoute, (c) => {
  return c.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    localStoragePath: c.var.localStoragePath,
  });
});

export default health;
