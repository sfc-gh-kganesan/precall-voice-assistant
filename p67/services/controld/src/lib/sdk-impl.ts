/**
 * @preserve
 * @p67/workflow-sdk
 *
 * Workflow SDK Implementation for P67 platform
 */

import {
    type Binds,
    type CortexAgentOptions,
    type CortexAgentResponse,
    type CortexAnalystResponse,
    type EmailOptions,
    type P67Config,
    P67ConfigSchema,
    type P67ConfigValue,
    P67ConfigValueSchema,
    type QueryResult,
    type SnowflakeStatement,
    type WorkflowSDK,
} from '@p67/workflow-sdk';
import snowflake from 'snowflake-sdk';
import type { Manifest } from './manifest';
import type { ValueManager } from './value-manager';

/**
 * P67 Agent SDK Client
 * Encapsulates all API functions for interacting with Snowflake and Cortex services
 */
export class WorkflowSDKImpl implements WorkflowSDK {
    private cachedConnection: snowflake.Connection | null = null;
    private isConnecting = false;
    private connectionPromise: Promise<snowflake.Connection> | null = null;
    private config: P67Config;

    constructor(config: P67Config) {
        this.config = P67ConfigSchema.parse(config);
    }

    private getSnowflakeConnectionOptions(
        cfg: P67ConfigValue,
    ): snowflake.ConnectionOptions {
        return {
            account: cfg.account ?? '',
            username: cfg.username ?? '',
            authenticator: cfg.authenticator ?? '',
            accessUrl: cfg.accessUrl,
            token: cfg.token ?? undefined,
            password: cfg.password ?? undefined,
            warehouse: cfg.warehouse ?? '',
            database: cfg.database ?? '',
            schema: cfg.schema ?? '',
        };
    }

    private cfg(config_name?: string): P67ConfigValue {
        if (config_name) {
            if (!this.config.snowflakeConfig.has(config_name)) {
                throw new Error(`Config ${config_name} not found`);
            }
            return P67ConfigValueSchema.parse(
                this.config.snowflakeConfig.get(config_name),
            );
        }
        // Get the only one if it exists
        if (this.config.snowflakeConfig.size === 0) {
            throw new Error('No Snowflake configurations available');
        }
        if (this.config.snowflakeConfig.size === 1) {
            return P67ConfigValueSchema.parse(
                this.config.snowflakeConfig.values().next().value,
            );
        }
        throw new Error(
            'Multiple Snowflake configs found, but no config name provided',
        );
    }

    /**
     * Checks if the cached connection is healthy
     * @returns {Promise<boolean>} True if connection is healthy, false otherwise
     */
    private async isConnectionHealthy(): Promise<boolean> {
        if (!this.cachedConnection) {
            return false;
        }

        try {
            await new Promise((resolve, reject) => {
                this.cachedConnection?.execute({
                    sqlText: 'SELECT 1',
                    complete: (err, _stmt, _rows) => {
                        if (err) reject(err);
                        else resolve(true);
                    },
                });
            });
            return true;
        } catch {
            this.cachedConnection = null;
            return false;
        }
    }

    /**
     * Establishes a connection to Snowflake with caching and connection reuse
     * Uses configuration provided via the P67Config constructor argument (optionally keeyed by config_name)
     * @returns {Promise<snowflake.Connection>} Connected Snowflake connection
     * @throws {Error} If required configuration values are missing or connection fails
     */
    private async getSnowflakeConnection(
        config_name?: string,
    ): Promise<snowflake.Connection> {
        const cfg = this.cfg(config_name);
        if (this.cachedConnection) {
            const healthy = await this.isConnectionHealthy();
            if (healthy) {
                return this.cachedConnection;
            }
        }

        if (this.isConnecting && this.connectionPromise) {
            return this.connectionPromise;
        }

        this.isConnecting = true;
        this.connectionPromise = new Promise((resolve, reject) => {
            const connection = snowflake.createConnection(
                this.getSnowflakeConnectionOptions(cfg),
            );

            connection.connect((err, conn) => {
                this.isConnecting = false;

                if (err) {
                    this.cachedConnection = null;
                    this.connectionPromise = null;
                    reject(
                        new Error(
                            `Failed to connect to Snowflake: ${err.message}`,
                        ),
                    );
                } else {
                    this.cachedConnection = conn;
                    resolve(conn);
                }
            });
        });

        return this.connectionPromise;
    }

    /**
     * Checks if a SQL query is a read-only SELECT statement
     * Allows SELECT, WITH (CTE), SHOW, and DESCRIBE statements
     * Rejects DML (INSERT, UPDATE, DELETE) and DDL (CREATE, ALTER, DROP) statements
     *
     * @param {string} sql - SQL query to validate
     * @returns {boolean} True if query is read-only
     * @throws {Error} If query contains multiple statements
     */
    private isSelectQuery(sql: string): boolean {
        const trimmed = sql.trim();
        const withoutComments = trimmed
            .replace(/^--.*$/gm, '')
            .replace(/\/\*[\s\S]*?\*\//g, '')
            .trim();

        if (withoutComments.includes(';')) {
            throw new Error(
                'Multiple statements are not allowed. Only single SELECT queries are permitted.',
            );
        }

        const firstKeyword = withoutComments.split(/\s+/)[0]?.toUpperCase();

        return (
            firstKeyword === 'SELECT' ||
            firstKeyword === 'WITH' ||
            firstKeyword === 'SHOW' ||
            firstKeyword === 'DESCRIBE' ||
            firstKeyword === 'DESC'
        );
    }

    /**
     * Executes a SQL query against Snowflake
     * Internal function - use executeQueryReadOnly for read-only queries
     *
     * @param {SnowflakeStatement} stmt - Snowflake statement to execute
     *   - `sqlText`: SQL text to execute
     *   - `binds`: Binds to use for the statement
     * @param {string} [config_name] - Name of the config to use, if null, the only one will be used
     * @returns {Promise<QueryResult>} Query results with statement and rows
     * @throws {Error} If query execution fails
     */
    private async executeQuery(
        stmt: SnowflakeStatement,
        config_name?: string,
    ): Promise<QueryResult> {
        const conn = await this.getSnowflakeConnection(config_name);
        return new Promise((resolve, reject) => {
            conn.execute({
                sqlText: stmt.sqlText,
                binds: stmt.binds || undefined,
                complete: (err, stmt, rows) => {
                    if (err) {
                        reject(
                            new Error(`Query execution failed: ${err.message}`),
                        );
                    } else {
                        resolve({ statement: stmt, rows: rows || [] });
                    }
                },
            });
        });
    }

    /**
     * Gets a parameter from the 'parameters' field of the config
     * @param name - The name of the parameter
     * @param config_name - The name of the config to use, if null, the only one will be used
     * @returns The value of the parameter or undefined if the parameter is not found
     */
    getParameter(name: string, config_name?: string): string | undefined {
        const cfg = this.cfg(config_name);
        return cfg.parameters?.[name];
    }

    async executeQueryReadOnly(
        stmt: SnowflakeStatement,
        config_name?: string,
    ): Promise<QueryResult> {
        if (!this.isSelectQuery(stmt.sqlText)) {
            throw new Error(
                'Only SELECT queries are allowed. DML (INSERT, UPDATE, DELETE) and DDL (CREATE, ALTER, DROP) statements are not permitted.',
            );
        }
        return this.executeQuery(stmt, config_name);
    }

    /**
     * Queries Cortex Analyst with a natural language question
     * Uses the Snowflake Cortex Analyst API to convert questions to SQL and execute them
     *
     * @param {string} question - Natural language question to ask
     * @param {string} [semanticModel] - Path to semantic model file (stage path or @stage/file.yaml)
     *                                   Defaults to CORTEX_ANALYST_SEMANTIC_MODEL env var
     * @param {string} [config_name] - Name of the config to use, if null, the only one will be used
     * @returns {Promise<CortexAnalystResponse>} Response with success status and data or error
     * @throws Never throws - returns error in response object
     *
     * @example
     * const response = await sdk.queryCortexAnalyst(
     *   'What were the top 5 products by revenue last month?',
     *   '@my_stage/semantic_model.yaml'
     * );
     * if (response.success) {
     *   console.log(response.data);
     * } else {
     *   console.error(response.error);
     * }
     */
    async queryCortexAnalyst(
        question: string,
        semanticModel?: string,
        config_name?: string,
    ): Promise<CortexAnalystResponse> {
        const cfg = this.cfg(config_name);
        try {
            const model =
                semanticModel || process.env.CORTEX_ANALYST_SEMANTIC_MODEL;

            if (!model) {
                throw new Error(
                    'CORTEX_ANALYST_SEMANTIC_MODEL environment variable is required or semantic model must be provided',
                );
            }

            const headers = {
                Authorization: `Bearer ${cfg.token}`,
                'Content-Type': 'application/json',
            };

            const url = `${cfg.accessUrl}/api/v2/cortex/analyst/message`;

            const payload = {
                messages: [
                    {
                        role: 'user',
                        content: [
                            {
                                type: 'text',
                                text: question,
                            },
                        ],
                    },
                ],
                semantic_model_file: model,
            };

            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
                signal: AbortSignal.timeout(180000),
            });

            if (response.ok) {
                const data = await response.json();
                return { success: true, data };
            } else {
                const errorText = await response.text();
                return {
                    success: false,
                    error: `HTTP ${response.status}: ${errorText}`,
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : String(error),
            };
        }
    }

    /**
     * Calls a Cortex Agent with a question and streams the response
     * Supports conversational context via parentMessageId
     *
     * @param {string} question - Question or message to send to the agent
     * @param {CortexAgentOptions} [options] - Configuration options
     * @param {string} [options.agentDatabase] - Database containing the agent (defaults to config database)
     * @param {string} [options.agentSchema] - Schema containing the agent (defaults to config schema)
     * @param {string} [options.agentName] - Name of the agent (required)
     * @param {string} [options.parentMessageId] - Parent message ID for conversation continuity (defaults to '0')
     * @param {Function} [options.onStream] - Callback for streaming events
     * @returns {Promise<CortexAgentResponse>} Response with success status, data, and debugging info
     * @throws Never throws - returns error in response object
     *
     * @example
     * const response = await sdk.callCortexAgent('What is the weather today?', {
     *   agentDatabase: 'MY_DB',
     *   agentSchema: 'MY_SCHEMA',
     *   agentName: 'weather_agent',
     *   onStream: (event) => {
     *     console.log(`Event: ${event.eventName}`, event.data);
     *   }
     * });
     *
     * if (response.success) {
     *   console.log(response.data.message.content);
     * } else {
     *   console.error(response.error);
     *   console.error('Request:', response.request);
     * }
     */
    async callCortexAgent(
        question: string,
        options?: CortexAgentOptions,
        config_name?: string,
    ): Promise<CortexAgentResponse> {
        const cfg = this.cfg(config_name);
        try {
            const database = options?.agentDatabase || cfg.database;
            const schema = options?.agentSchema || cfg.schema;
            const name = options?.agentName;
            const parentMessageId = options?.parentMessageId || '0';
            const onStream = options?.onStream;

            if (!database) {
                throw new Error(
                    'AGENT_DATABASE is required via configuration or options',
                );
            }

            if (!schema) {
                throw new Error(
                    'AGENT_SCHEMA is required via configuration or options',
                );
            }

            if (!name) {
                throw new Error('AGENT_NAME is required via options');
            }

            const token = cfg.token;
            if (!token) {
                throw new Error('SNOWFLAKE_TOKEN is required in configuration');
            }

            if (token === 'undefined' || !token.trim()) {
                throw new Error(
                    'SNOWFLAKE_TOKEN must be a valid token, not empty or undefined',
                );
            }

            const headers = {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
                Accept: 'application/json',
            };

            const url = `${cfg.accessUrl}/api/v2/databases/${database}/schemas/${schema}/agents/${name}:run`;

            const payload = {
                parent_message_id: parentMessageId,
                messages: [
                    {
                        role: 'user',
                        content: [
                            {
                                type: 'text',
                                text: question,
                            },
                        ],
                    },
                ],
            };

            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
                signal: AbortSignal.timeout(120000),
            });

            const sanitizedHeaders = {
                'Content-Type': headers['Content-Type'],
                Accept: headers.Accept,
            };

            if (!response.ok) {
                const errorText = await response.text();
                return {
                    success: false,
                    status_code: response.status,
                    error: errorText,
                    request: {
                        url,
                        headers: sanitizedHeaders,
                        payload,
                    },
                };
            }

            let finalMessage: { content?: string } | null = null;
            let currentEventName: string | null = null;

            if (!response.body) {
                return {
                    success: false,
                    status_code: response.status,
                    error: 'No response body received',
                    request: {
                        url,
                        headers: sanitizedHeaders,
                        payload,
                    },
                };
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            try {
                while (true) {
                    const { done, value } = await reader.read();

                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (!line.trim()) continue;

                        if (line.startsWith('event: ')) {
                            currentEventName = line.substring(7).trim();
                        } else if (line.startsWith('data: ')) {
                            const dataStr = line.substring(6).trim();

                            if (dataStr === '[DONE]') {
                                reader.cancel();
                                break;
                            }

                            try {
                                const eventData = JSON.parse(dataStr);

                                if (onStream && currentEventName) {
                                    onStream({
                                        eventName: currentEventName,
                                        data: eventData,
                                    });
                                }

                                if (
                                    currentEventName === 'response' &&
                                    eventData.content
                                ) {
                                    finalMessage = eventData;
                                }
                            } catch {
                                throw new Error(
                                    `Failed to parse event data: ${dataStr}`,
                                );
                            }
                        }
                    }
                }
            } finally {
                reader.releaseLock();
            }

            if (!finalMessage) {
                return {
                    success: false,
                    status_code: response.status,
                    error: 'No complete message received from agent',
                    request: {
                        url,
                        headers: sanitizedHeaders,
                        payload,
                    },
                };
            }

            return {
                success: true,
                status_code: 200,
                data: {
                    message: {
                        role: 'agent',
                        content: finalMessage.content || [],
                    },
                },
                request: {
                    url,
                    headers: sanitizedHeaders,
                    payload,
                },
            };
        } catch (error) {
            return {
                success: false,
                status_code: 0,
                error: error instanceof Error ? error.message : String(error),
            };
        }
    }

    async email(options: EmailOptions, config_name?: string): Promise<boolean> {
        var cfg = this.cfg(config_name);
        var integration_name = options.integration_name;
        if (!integration_name) {
            if (cfg.email_integration) {
                integration_name = cfg.email_integration;
            } else {
                throw new Error(
                    `'integration_name' is required in options or config`,
                );
            }
        }
        const binds: Binds = [
            integration_name,
            options.email_addresses.join(','),
            options.subject,
            options.body,
            options.content_type || 'text/plain',
        ];
        return this.executeQuery(
            {
                sqlText: `CALL SYSTEM$SEND_EMAIL(?, ?, ?, ?, ?)`,
                binds: binds,
            },
            config_name,
        ).then((result) => {
            return result.rows.length > 0;
        });
    }

    /**
     * Closes the cached Snowflake connection
     * Call this when shutting down to properly cleanup resources
     *
     * @returns {Promise<void>}
     *
     * @example
     * // ... use sdk ...
     * await sdk.close();
     */
    async close(): Promise<void> {
        if (this.cachedConnection) {
            return new Promise((resolve) => {
                this.cachedConnection?.destroy((err) => {
                    if (err) {
                        // Log error but still resolve - connection is being destroyed anyway
                        console.error(
                            `Error closing connection: ${err.message}`,
                        );
                    }
                    this.cachedConnection = null;
                    this.connectionPromise = null;
                    this.isConnecting = false;
                    resolve();
                });
            });
        }
    }
}

function validateConfig(config: P67ConfigValue): P67ConfigValue {
    // Patch config and fix accessURL if it's missing
    if (!config.accessUrl) {
        if (config.account) {
            const accountLocator = config.account
                .replaceAll('_', '-')
                .toLowerCase();
            config.accessUrl = `https://${accountLocator}.snowflakecomputing.com`;
        }
    }

    // Determine and set authenticator as appropriate
    if (!config.authenticator) {
        if (config.token) {
            config.authenticator = 'PROGRAMMATIC_ACCESS_TOKEN';
        } else if (config.password) {
            config.authenticator = 'PASSWORD';
        }
    }

    if (config.authenticator === 'PROGRAMMATIC_ACCESS_TOKEN' && !config.token) {
        throw new Error(
            'SNOWFLAKE_TOKEN is required for PROGRAMMATIC_ACCESS_TOKEN authenticator',
        );
    }
    if (config.authenticator === 'PASSWORD' && !config.password) {
        throw new Error(
            'SNOWFLAKE_PASSWORD is required for PASSWORD authenticator',
        );
    }
    if (config.token && config.password) {
        throw new Error(
            'Both "token" and "password" are set in config; only one authentication method can be used.',
        );
    }

    return config;
}

/*
 * Hydrates the config from the manifest
 * @param manifest - The manifest to hydrate the config from
 * @returns The hydrated config
 *
 * TODO(nwiegand): Take in the secrets manager here and resolve the secrets here.
 */
export async function hydrateConfig(
    manifest: Manifest,
    valueManager: ValueManager,
): Promise<P67Config> {
    const config = new Map<string, P67ConfigValue>();

    const parameters = new Map<string, string>();
    for (const c of manifest.config) {
        if (c.parameters) {
            console.log('🌶️ ✅ 🔥 MANIFEST PARAMETERS', c.parameters);
            for (const [key, value] of Object.entries(c.parameters)) {
                console.log('🌶️ ✅ 🔥 MANIFEST PARAMETER', key, value);
                parameters.set(key, (await valueManager.get(value)) ?? '');
            }
        }
    }

    for (const c of manifest.config) {
        const validated = validateConfig({
            account: await valueManager.get(c.account),
            username: await valueManager.get(c.username),
            authenticator: await valueManager.get(c.authenticator),
            accessUrl: await valueManager.get(c.accessUrl),
            token: await valueManager.get(c.token),
            password: await valueManager.get(c.password),
            warehouse: await valueManager.get(c.warehouse),
            database: await valueManager.get(c.database),
            schema: await valueManager.get(c.schema),
            email_integration: await valueManager.get(c.email_integration),
            parameters: Object.fromEntries(parameters),
        });
        config.set(c.config_name, validated);
    }

    return { snowflakeConfig: config };
}
