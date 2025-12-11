import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { serve } from '@hono/node-server';
import { errorHandler } from './middleware/error-handler.js';
import { env, Env } from './middleware/env.js';
import { initLogger } from './middleware/logger.js';
import { getPort } from './lib/env.js';
import apiRouter from './routes/api.js';
import buildConfig from './config.js';

const app = new Hono<Env>();
const config = buildConfig();

console.log(JSON.stringify(config, null, 2));

app.use(env(config));
app.use(initLogger(config));
app.use(errorHandler);
app.use(cors());

app.route('/api', apiRouter);
const port = getPort();

console.log(`Server listening on port ${port}`);

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
