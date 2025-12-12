import { OpenAPIHono } from '@hono/zod-openapi';
import { cors } from 'hono/cors';
import { serve } from '@hono/node-server';
import { swaggerUI } from '@hono/swagger-ui';
import { errorHandler } from './middleware/error-handler.js';
import { env, Env } from './middleware/env.js';
import { initLogger } from './middleware/logger.js';
import { getPort } from './lib/env.js';
import apiRouter from './routes/api.js';
import buildConfig from './config.js';

const app = new OpenAPIHono<Env>();
const config = buildConfig();

console.log(JSON.stringify(config, null, 2));

app.use(env(config));
app.use(initLogger(config));
app.use(errorHandler);
app.use(cors());

app.route('/api', apiRouter);

app.doc('/openapi.json', {
  openapi: '3.1.0',
  info: {
    title: 'P67 Harness API',
    version: '1.0.0',
    description: 'Workflow harness service API',
  },
  servers: [
    {
      url: 'http://localhost:3001',
      description: 'Development server',
    },
  ],
});

app.get('/docs', swaggerUI({ url: '/openapi.json' }));

const port = getPort();

console.log(`Server listening on port ${port}`);
console.log(`OpenAPI schema available at http://localhost:${port}/openapi.json`);
console.log(`Swagger UI available at http://localhost:${port}/docs`);

const server = serve({
  fetch: app.fetch,
  port,
});

process.on('SIGTERM', () => {
  server.close((err) => {
    if (err) {
      console.error(err);
      process.exit(1);
    }
    process.exit(0);
  });
});
