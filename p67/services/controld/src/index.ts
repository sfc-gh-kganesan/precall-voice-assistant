import apiRouter from '@controld/routes/api.js';
import { buildServer } from '@controld/server.js';

const server = await buildServer();
await server.register(apiRouter, { prefix: '/api' });

const start = async () => {
  try {
    await server.listen({ port: server.config.port, host: '0.0.0.0' });
    console.log(
      '===================================================================================',
    );
    console.log(`Google Client ID: ${server.config.oauth.google.clientId.slice(0, 5)}...`);
    console.log(`Google Client Secret: ${server.config.oauth.google.clientSecret.slice(0, 5)}...`);
    console.log(`Google Redirect URI: ${server.config.oauth.google.redirectUri}`);
    console.log(
      '===================================================================================',
    );
    console.log(`Server listening on port ${server.config.port}`);
    console.log(`OpenAPI schema available at http://localhost:${server.config.port}/docs/json`);
    console.log(`Swagger UI available at http://localhost:${server.config.port}/docs`);
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
};

process.on('SIGTERM', async () => {
  server.log.info('SIGTERM received, shutting down gracefully');
  try {
    await server.close();
    server.log.info('Server closed successfully');
    process.exit(0);
  } catch (error) {
    server.log.error({ error }, 'Error during shutdown');
    process.exit(1);
  }
});

process.on('SIGINT', async () => {
  server.log.info('SIGINT received, shutting down gracefully');
  try {
    await server.close();
    server.log.info('Server closed successfully');
    process.exit(0);
  } catch (error) {
    server.log.error({ error }, 'Error during shutdown');
    process.exit(1);
  }
});

start();
