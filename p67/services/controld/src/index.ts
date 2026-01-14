import apiRouter from '@controld/routes/api.js';
import { buildServer } from '@controld/server.js';

const server = await buildServer();
await server.register(apiRouter, { prefix: '/api' });

const start = async () => {
    try {
        await server.listen({ port: server.config.port, host: '0.0.0.0' });
        server.log.debug(
            `Google Client ID: ${server.config.oauth.google.clientId.slice(0, 5)}...`,
        );
        server.log.debug(
            `Google Client Secret: ${server.config.oauth.google.clientSecret.slice(0, 5)}...`,
        );
        server.log.debug(
            `Google Redirect URI: ${server.config.oauth.google.redirectUri}`,
        );
        server.log.debug(
            `OpenAPI schema available at http://localhost:${server.config.port}/docs/json`,
        );
        server.log.debug(
            `Swagger UI available at http://localhost:${server.config.port}/docs`,
        );
        if (server.config.debug.enableDefaultUser) {
            server.log.debug(
                `Running in debug mode with default user: ${server.config.debug.defaultUser}`,
            );
        }
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
