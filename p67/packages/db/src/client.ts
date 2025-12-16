import { PrismaClient } from '@prisma/client';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';

export const createPrismaClient = (databaseUrl: string) => {
  if (!databaseUrl) {
    throw new Error('Database URL is required');
  }

  // Create PostgreSQL connection pool
  const pool = new pg.Pool({ connectionString: databaseUrl });

  // Create Prisma driver adapter for PostgreSQL
  const adapter = new PrismaPg(pool);

  return new PrismaClient({
    adapter,
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });
};
