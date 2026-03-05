/**
 * SPCS SQL Execution Helper
 *
 * Provides a lightweight Snowflake connection for executing SPCS management
 * SQL (EXECUTE JOB SERVICE, PUT, DESCRIBE SERVICE, etc.) from within
 * a running SPCS service container.
 *
 * Uses the auto-provisioned OAuth token at /snowflake/session/token.
 */

import { readFileSync } from 'node:fs';
import snowflake from 'snowflake-sdk';

type SnowflakeConnection = ReturnType<typeof snowflake.createConnection>;

let cachedConnection: SnowflakeConnection | null = null;

/**
 * Read the SPCS session token from the well-known path.
 */
function readSessionToken(): string {
    return readFileSync('/snowflake/session/token', 'utf-8').trim();
}

/**
 * Get or create a Snowflake connection using the SPCS session token.
 */
export async function getConnection(): Promise<SnowflakeConnection> {
    if (cachedConnection) {
        return cachedConnection;
    }

    const host = process.env.SNOWFLAKE_HOST;
    const account = process.env.SNOWFLAKE_ACCOUNT;

    if (!host || !account) {
        throw new Error(
            'SPCS environment variables SNOWFLAKE_HOST and SNOWFLAKE_ACCOUNT are required',
        );
    }

    const token = readSessionToken();

    const connection = snowflake.createConnection({
        accessUrl: `https://${host}`,
        account,
        token,
        authenticator: 'OAUTH',
        // In SPCS, database/schema/warehouse are inherited from the service context
        database: process.env.SNOWFLAKE_DATABASE,
        schema: process.env.SNOWFLAKE_SCHEMA,
    });

    return new Promise((resolve, reject) => {
        connection.connect((err) => {
            if (err) {
                reject(
                    new Error(
                        `SPCS Snowflake connection failed: ${err.message}`,
                    ),
                );
            } else {
                cachedConnection = connection;
                resolve(connection);
            }
        });
    });
}

/**
 * Execute a SQL statement and return the rows.
 */
export async function executeSql(
    sql: string,
): Promise<Record<string, unknown>[]> {
    const conn = await getConnection();
    return new Promise((resolve, reject) => {
        conn.execute({
            sqlText: sql,
            complete: (err, _stmt, rows) => {
                if (err) {
                    reject(
                        new Error(
                            `SQL execution failed: ${err.message}\nSQL: ${sql}`,
                        ),
                    );
                } else {
                    resolve((rows as Record<string, unknown>[]) ?? []);
                }
            },
        });
    });
}

/**
 * Execute multiple SQL statements sequentially.
 */
export async function executeSqlBatch(statements: string[]): Promise<void> {
    for (const sql of statements) {
        await executeSql(sql);
    }
}
