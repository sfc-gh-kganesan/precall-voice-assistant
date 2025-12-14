import apiRouter from './routes/api.js';
import { buildServer } from './server.js';

const server = await buildServer();
await server.register(apiRouter, { prefix: '/api' });

const start = async () => {
  try {
    await server.listen({ port: server.config.port, host: '0.0.0.0' });
    console.log(`Server listening on port ${server.config.port}`);
    console.log(`OpenAPI schema available at http://localhost:${server.config.port}/docs/json`);
    console.log(`Swagger UI available at http://localhost:${server.config.port}/docs`);
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
};

process.on('SIGTERM', async () => {
  await server.close();
  process.exit(0);
});

start();
