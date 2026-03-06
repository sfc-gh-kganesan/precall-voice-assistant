/**
 * SPCS SQL Execution Helper
 *
 * Provides Snowflake connections for executing SPCS management
 * SQL (EXECUTE JOB SERVICE, PUT, DESCRIBE SERVICE, etc.) from within
 * a running SPCS service container.
 *
 * Uses the auto-provisioned OAuth token at /snowflake/session/token.
 *
 * Each executeSql call creates a fresh connection to avoid deadlocks
 * when concurrent EXECUTE JOB SERVICE statements (e.g. top-level
 * workflow + nested subworkflows) block on the same session.
 */

import { readFileSync } from 'node:fs';
import snowflake from 'snowflake-sdk';

type SnowflakeConnection = ReturnType<typeof snowflake.createConnection>;

/**
 * Read the SPCS session token from the well-known path.
 */
function readSessionToken(): string {
    return readFileSync('/snowflake/session/token', 'utf-8').trim();
}

/**
 * Create a new Snowflake connection using the SPCS session token.
 */
function createSPCSConnection(): Promise<SnowflakeConnection> {
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
                resolve(connection);
            }
        });
    });
}

/**
 * Execute a SQL statement and return the rows.
 *
 * Creates a fresh connection for each call so that long-running
 * statements (like EXECUTE JOB SERVICE) don't block other callers.
 */
export async function executeSql(
    sql: string,
): Promise<Record<string, unknown>[]> {
    const conn = await createSPCSConnection();
    try {
        return await new Promise((resolve, reject) => {
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
    } finally {
        conn.destroy(() => {});
    }
}

/**
 * Execute multiple SQL statements sequentially.
 */
export async function executeSqlBatch(statements: string[]): Promise<void> {
    for (const sql of statements) {
        await executeSql(sql);
    }
}
