import { FastifyPluginAsync } from 'fastify';
import fp from 'fastify-plugin';
import type { PrismaClient } from '@p67/db/generated/prisma/client.js';
import { createPrismaClient } from './client.js';

// Plugin options interface
export interface DatabasePluginOptions {
  databaseUrl: string;
}

// Extend Fastify types to include prisma
declare module 'fastify' {
  interface FastifyInstance {
    db: PrismaClient;
  }
}

const plugin: FastifyPluginAsync<DatabasePluginOptions> = async (fastify, options) => {
  const { databaseUrl } = options;

  if (!databaseUrl) {
    throw new Error('databaseUrl is required for database plugin');
  }

  // Create Prisma client with provided URL
  const db = createPrismaClient(databaseUrl);

  // Test database connection on startup
  try {
    await db.$connect();
    fastify.log.info('Database connected successfully');
  } catch (error) {
    fastify.log.error({ error }, 'Failed to connect to database');
    throw error;
  }

  // Decorate Fastify instance with Prisma client
  fastify.decorate('db', db);

  // Graceful shutdown: disconnect from database when Fastify closes
  fastify.addHook('onClose', async (instance) => {
    instance.log.info('Disconnecting from database');
    await instance.db.$disconnect();
  });
};

// Use fastify-plugin to ensure plugin is registered at root level
export const databasePlugin = fp(plugin, {
  name: 'database',
});
