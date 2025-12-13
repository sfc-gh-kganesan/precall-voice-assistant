import cors from '@fastify/cors';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import multipart from '@fastify/multipart';
import Fastify, { FastifyInstance } from 'fastify';
import { loadConfig, ServerConfig } from './config.js';
import {
  serializerCompiler,
  validatorCompiler,
  type ZodTypeProvider,
} from 'fastify-type-provider-zod';

declare module 'fastify' {
  interface FastifyInstance {
    config: ServerConfig;
  }
}

export async function buildServer(): Promise<FastifyInstance> {
  const config = loadConfig();

  const server = Fastify({
    logger: {
      level: 'debug',
      transport: {
        target: 'pino-pretty',
        options: {
          translateTime: 'SYS:standard',
          singleLine: false,
        },
      },
    },
  }).withTypeProvider<ZodTypeProvider>();

  server.decorate('config', config);
  server.setValidatorCompiler(validatorCompiler);
  server.setSerializerCompiler(serializerCompiler);

  await server.register(multipart);

  await server.register(cors, {
    origin: true,
  });

  await server.register(swagger, {
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

  await server.register(swaggerUi, {
    routePrefix: '/docs',
  });

  return server;
}
