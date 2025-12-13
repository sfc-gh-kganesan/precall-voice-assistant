import cors from '@fastify/cors';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import Fastify from 'fastify';
import {
  serializerCompiler,
  validatorCompiler,
  type ZodTypeProvider,
} from 'fastify-type-provider-zod';
import buildConfig from './config.js';
import apiRouter from './routes/api.js';

const config = buildConfig();

console.log(JSON.stringify(config, null, 2));

const fastify = Fastify({
  logger: {
    level: config.nodeEnv === 'development' ? 'info' : 'warn',
  },
}).withTypeProvider<ZodTypeProvider>();

fastify.setValidatorCompiler(validatorCompiler);
fastify.setSerializerCompiler(serializerCompiler);

await fastify.register(cors, {
  origin: true,
});

await fastify.register(swagger, {
  openapi: {
    info: {
      title: 'P67 Controld API',
      description: 'Control plane service API',
      version: '1.0.0',
    },
    servers: [
      {
        url: `http://localhost:${config.port}`,
        description: 'Development server',
      },
    ],
  },
});

await fastify.register(swaggerUi, {
  routePrefix: '/docs',
});

await fastify.register(apiRouter, { prefix: '/api' });

const start = async () => {
  try {
    await fastify.listen({ port: config.port, host: '0.0.0.0' });
    console.log(`Server listening on port ${config.port}`);
    console.log(`OpenAPI schema available at http://localhost:${config.port}/docs/json`);
    console.log(`Swagger UI available at http://localhost:${config.port}/docs`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

process.on('SIGTERM', async () => {
  await fastify.close();
  process.exit(0);
});

start();
