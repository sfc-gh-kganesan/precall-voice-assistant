import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';
import { PrismaClient } from './generated/prisma/client.js';

export const createPrismaClient = (databaseUrl: string): PrismaClient => {
    if (!databaseUrl) {
        throw new Error('Database URL is required');
    }

    // Create PostgreSQL connection pool
    // Enable SSL for Snowflake Postgres connections (self-signed certificates)
    const url = new URL(databaseUrl);
    const sslParam = url.searchParams.get('sslmode');
    const useSSL =
        sslParam === 'require' || databaseUrl.includes('.snowflake.app');
    const pool = new pg.Pool({
        connectionString: databaseUrl,
        ...(useSSL && { ssl: { rejectUnauthorized: false } }),
    });

    // Create Prisma driver adapter for PostgreSQL
    const adapter = new PrismaPg(pool);

    return new PrismaClient({
        adapter,
        log:
            process.env.NODE_ENV === 'development'
                ? ['query', 'error', 'warn']
                : ['error'],
    });
};
