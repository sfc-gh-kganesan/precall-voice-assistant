/**
 * @preserve
 * @p67/workflow-sdk
 *
 * Workflow SDK Implementation for P67 platform
 */

import * as child_process from 'node:child_process';
import * as crypto from 'node:crypto';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import * as readline from 'node:readline';
import {
    type Binds,
    type CortexAgentOptions,
    type CortexAgentResponse,
    type CortexAnalystResponse,
    type CortexChoice,
    type CortexChoiceMessage,
    type CortexCodeOptions,
    type CortexCodeResponse,
    type CortexCompleteOptions,
    type CortexCompleteRequestInfo,
    type CortexCompleteResponse,
    type CortexInferenceRegion,
    type CortexMessage,
    type CortexStreamChoice,
    type CortexStreamChunk,
    type CortexStreamDelta,
    type CortexStreamDeltaToolCall,
    type CortexTokenUsage,
    type EmailOptions,
    type HttpRequestOptions,
    type HttpResponse,
    type InterruptOptions,
    type P67Config,
    P67ConfigSchema,
    type P67ConfigValue,
    P67ConfigValueSchema,
    type QueryResult,
    type SnowflakeStatement,
    type SubworkflowOptions,
    type SubworkflowResponse,
    type WorkflowSDK,
} from '@p67/workflow-sdk';
import snowflake from 'snowflake-sdk';
import type { Manifest } from './manifest.js';
import {
    type InterruptMessage,
    MessageSchema,
    MessageType,
    makeInterruptMessage,
    type ResumeInterruptMessage,
} from './runtime/schema.js';
import type { ValueManager } from './value-manager.js';

/**
 * Function type for resolving OAuth tokens
 */
export type OAuthTokenResolver = (oauthRef: string) => Promise<string>;

/**
 * Configuration options for WorkflowSDKImpl
 */
export interface WorkflowSDKImplOptions {
    config: P67Config;
    /** Optional OAuth token resolver for httpRequest with oauthRef */
    oauthTokenResolver?: OAuthTokenResolver;
}

/**
 * P67 Agent SDK Client
 * Encapsulates all API functions for interacting with Snowflake and Cortex services
 */
export class WorkflowSDKImpl implements WorkflowSDK {
    private cachedConnection: snowflake.Connection | null = null;
    private isConnecting = false;
    private connectionPromise: Promise<snowflake.Connection> | null = null;
    private config: P67Config;
    private oauthTokenResolver?: OAuthTokenResolver;
    private pendingInterrupts: Map<
        string,
        {
            resolve: (value: unknown) => void;
            reject: (error: Error) => void;
        }
    > = new Map();

    constructor(configOrOptions: P67Config | WorkflowSDKImplOptions) {
        if ('snowflakeConfig' in configOrOptions) {
            // Legacy constructor: just P67Config
            this.config = P67ConfigSchema.parse(configOrOptions);
        } else {
            // New constructor: WorkflowSDKImplOptions
            this.config = P67ConfigSchema.parse(configOrOptions.config);
            this.oauthTokenResolver = configOrOptions.oauthTokenResolver;
        }

        // Listen for resume messages from parent process (used in child process context)
        this.setupResumeListener();
    }

    /**
     * Sets up listener for ResumeInterrupt messages from parent process
     */
    private setupResumeListener(): void {
        const rl = readline.createInterface({ input: process.stdin });
        rl.on('line', (line) => {
            if (!line.trim()) return;
            let message: unknown;
            try {
                message = JSON.parse(line);
            } catch {
                return;
            }
            console.log(
                `[SDK] Received message from parent:`,
                JSON.stringify(message),
            );
            const parsed = MessageSchema.safeParse(message);
            if (!parsed.success) {
                console.log(`[SDK] Failed to parse message:`, parsed.error);
                return;
            }

            if (parsed.data.type === MessageType.ResumeInterrupt) {
                const { interruptId, response } =
                    parsed.data as ResumeInterruptMessage;
                console.log(
                    `[SDK] Processing ResumeInterrupt for: ${interruptId}`,
                );
                const pending = this.pendingInterrupts.get(interruptId);
                if (pending) {
                    console.log(`[SDK] Found pending interrupt, resolving...`);
                    pending.resolve(response);
                    this.pendingInterrupts.delete(interruptId);
                } else {
                    console.log(
                        `[SDK] No pending interrupt found for: ${interruptId}`,
                    );
                }
            }
        });
    }

    private getSnowflakeConnectionOptions(
        cfg: P67ConfigValue,
    ): snowflake.ConnectionOptions {
        // Ensure accessUrl has protocol prefix - snowflake-sdk's url.parse() returns
        // hostname: null without it, breaking account extraction logic
        let accessUrl = cfg.accessUrl;
        if (
            accessUrl &&
            !accessUrl.startsWith('https://') &&
            !accessUrl.startsWith('http://')
        ) {
            accessUrl = `https://${accessUrl}`;
        }

        return {
            account: cfg.account ?? '',
            username: cfg.username ?? '',
            authenticator: cfg.authenticator ?? '',
            accessUrl,
            token: cfg.token ?? undefined,
            password: cfg.password ?? undefined,
            warehouse: cfg.warehouse ?? '',
            database: cfg.database ?? '',
            schema: cfg.schema ?? '',
        };
    }

    private cfg(config_name?: string): P67ConfigValue {
        let config: P67ConfigValue;
        if (config_name) {
            if (!this.config.snowflakeConfig.has(config_name)) {
                throw new Error(`Config ${config_name} not found`);
            }
            config = P67ConfigValueSchema.parse(
                this.config.snowflakeConfig.get(config_name),
            );
        } else if (this.config.snowflakeConfig.size === 0) {
            throw new Error('No Snowflake configurations available');
        } else if (this.config.snowflakeConfig.size === 1) {
            config = P67ConfigValueSchema.parse(
                this.config.snowflakeConfig.values().next().value,
            );
        } else {
            throw new Error(
                'Multiple Snowflake configs found, but no config name provided',
            );
        }

        // Ensure accessUrl has protocol prefix for HTTP calls
        if (
            config.accessUrl &&
            !config.accessUrl.startsWith('https://') &&
            !config.accessUrl.startsWith('http://')
        ) {
            config = { ...config, accessUrl: `https://${config.accessUrl}` };
        }

        return config;
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
            const connOpts = this.getSnowflakeConnectionOptions(cfg);
            console.log(`🔥[SDK] Creating Snowflake connection with options:`, {
                ...connOpts,
                token: connOpts.token ? '<redacted>' : undefined,
                password: connOpts.password ? '<redacted>' : undefined,
            });
            const connection = snowflake.createConnection(connOpts);

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
     *
     * @param {SnowflakeStatement} stmt - Snowflake statement to execute
     *   - `sqlText`: SQL text to execute
     *   - `binds`: Binds to use for the statement
     * @param {string} [config_name] - Name of the config to use, if null, the only one will be used
     * @returns {Promise<QueryResult>} Query results with statement and rows
     * @throws {Error} If query execution fails
     */
    async executeQuery(
        stmt: SnowflakeStatement,
        config_name?: string,
    ): Promise<QueryResult> {
        if (!stmt.sqlText) {
            const keys = Object.keys(stmt);
            throw new Error(
                `executeQuery requires 'sqlText' property, got keys: [${keys.join(', ')}]. Use { sqlText: '...' } not { sql: '...' }.`,
            );
        }
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
     * @returns The value of the parameter
     * @throws {Error} If the parameter is not found
     */
    getParameter(name: string, config_name?: string): string {
        const cfg = this.cfg(config_name);
        const value = cfg.parameters?.[name];
        if (value === undefined) {
            throw new Error(`Parameter '${name}' not found`);
        }
        return value;
    }

    /**
     * Gets all parameters from the 'parameters' field of the config
     * @param config_name - The name of the config to use, if null, the only one will be used
     * @returns The parameters as a record of name-value pairs
     */
    getParameters(config_name?: string): Record<string, string> {
        const cfg = this.cfg(config_name);
        return cfg.parameters || {};
    }

    async executeQueryReadOnly(
        stmt: SnowflakeStatement,
        config_name?: string,
    ): Promise<QueryResult> {
        if (!stmt.sqlText) {
            const keys = Object.keys(stmt);
            throw new Error(
                `executeQueryReadOnly requires 'sqlText' property, got keys: [${keys.join(', ')}]. Use { sqlText: '...' } not { sql: '...' }.`,
            );
        }
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

    /**
     * Makes an HTTP request to an external service
     * Supports automatic OAuth token injection via oauthRef
     */
    async httpRequest(options: HttpRequestOptions): Promise<HttpResponse> {
        try {
            const {
                url,
                method = 'GET',
                headers = {},
                body,
                oauthRef,
                timeout = 30000,
            } = options;

            // Build request headers
            const requestHeaders: Record<string, string> = { ...headers };

            // If oauthRef is provided, resolve the token and add Authorization header
            if (oauthRef) {
                if (!this.oauthTokenResolver) {
                    return {
                        success: false,
                        status: 0,
                        headers: {},
                        error: 'OAuth token resolver not configured. Cannot use oauthRef.',
                    };
                }

                try {
                    const accessToken = await this.oauthTokenResolver(oauthRef);
                    requestHeaders.Authorization = `Bearer ${accessToken}`;
                } catch (error) {
                    return {
                        success: false,
                        status: 0,
                        headers: {},
                        error: `Failed to resolve OAuth token "${oauthRef}": ${error instanceof Error ? error.message : String(error)}`,
                    };
                }
            }

            // Serialize body if it's an object
            let requestBody: string | undefined;
            if (body !== undefined) {
                if (typeof body === 'string') {
                    requestBody = body;
                } else {
                    requestBody = JSON.stringify(body);
                    // Set Content-Type if not already set
                    if (!requestHeaders['Content-Type']) {
                        requestHeaders['Content-Type'] = 'application/json';
                    }
                }
            }

            // Make the request
            const response = await fetch(url, {
                method,
                headers: requestHeaders,
                body: requestBody,
                signal: AbortSignal.timeout(timeout),
            });

            // Parse response headers
            const responseHeaders: Record<string, string> = {};
            response.headers.forEach((value, key) => {
                responseHeaders[key] = value;
            });

            // Parse response body
            let data: unknown;
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                try {
                    data = await response.json();
                } catch {
                    // If JSON parsing fails, try text
                    data = await response.text();
                }
            } else {
                data = await response.text();
            }

            const success = response.ok;

            if (success) {
                return {
                    success: true,
                    status: response.status,
                    headers: responseHeaders,
                    data,
                };
            } else {
                return {
                    success: false,
                    status: response.status,
                    headers: responseHeaders,
                    data,
                    error: `HTTP ${response.status}: ${response.statusText}`,
                };
            }
        } catch (error) {
            // Handle network errors, timeouts, etc.
            const errorMessage =
                error instanceof Error ? error.message : String(error);

            // Check for timeout
            if (
                errorMessage.includes('abort') ||
                errorMessage.includes('timeout')
            ) {
                return {
                    success: false,
                    status: 0,
                    headers: {},
                    error: `Request timeout: ${errorMessage}`,
                };
            }

            return {
                success: false,
                status: 0,
                headers: {},
                error: `Request failed: ${errorMessage}`,
            };
        }
    }

    /**
     * Pauses workflow execution and waits for human input.
     *
     * Sends an interrupt message to the parent process and waits for a resume message.
     * The workflow will block until a human provides input via the controld API.
     *
     * @param payload - JSON-serializable value to surface (question, form data, etc.)
     * @param options - Optional configuration
     * @returns The response provided by the human
     * @throws Error if timeout is reached (when specified) or if not running in child process
     */
    async interrupt<T = unknown>(
        payload: unknown,
        options?: InterruptOptions,
    ): Promise<T> {
        const interruptId = crypto.randomUUID();
        const timestamp = new Date().toISOString();

        // Create and send interrupt message to parent
        const message: InterruptMessage = makeInterruptMessage({
            interruptId,
            payload,
            nodeId: options?.nodeId,
            timestamp,
            notify: options?.notify,
        });

        console.log(`[SDK] Sending interrupt message: ${interruptId}`);
        process.stdout.write(`${JSON.stringify(message)}\n`);

        // Wait for response (long-poll pattern)
        // Use setInterval to keep the event loop alive while waiting
        return new Promise<T>((resolve, reject) => {
            // Keep-alive interval to prevent Node from exiting
            const keepAlive = setInterval(() => {
                // This keeps the event loop active
            }, 1000);

            this.pendingInterrupts.set(interruptId, {
                resolve: (value: unknown) => {
                    clearInterval(keepAlive);
                    console.log(`[SDK] Interrupt resolved: ${interruptId}`);
                    resolve(value as T);
                },
                reject: (error: Error) => {
                    clearInterval(keepAlive);
                    reject(error);
                },
            });

            // Optional timeout
            if (options?.timeout) {
                setTimeout(() => {
                    if (this.pendingInterrupts.has(interruptId)) {
                        clearInterval(keepAlive);
                        this.pendingInterrupts.delete(interruptId);
                        reject(
                            new Error(
                                `Interrupt timed out after ${options.timeout}ms`,
                            ),
                        );
                    }
                }, options.timeout);
            }
        });
    }

    /**
     * Maps region option to the appropriate header value for cross-region inference
     */
    private getRegionHeader(
        region?: CortexInferenceRegion,
    ): string | undefined {
        if (!region || region === 'auto') {
            return undefined;
        }

        // Map our region names to Snowflake's expected header values
        const regionMap: Record<string, string> = {
            'cross-cloud-any': 'cross-cloud',
            'aws-global': 'aws',
            'aws-us': 'aws-us',
            'aws-eu': 'aws-eu',
            'aws-apj': 'aws-apj',
            'azure-global': 'azure',
            'azure-us': 'azure-us',
            'azure-eu': 'azure-eu',
        };

        return regionMap[region];
    }

    /**
     * Normalizes messages input to array format
     */
    private normalizeMessages(
        messages: string | CortexMessage[],
    ): CortexMessage[] {
        if (typeof messages === 'string') {
            return [{ role: 'user', content: messages }];
        }
        return messages;
    }

    /**
     * Builds the request payload for Cortex Complete API
     */
    private buildCortexCompletePayload(
        options: CortexCompleteOptions,
        stream: boolean,
    ): Record<string, unknown> {
        const messages = this.normalizeMessages(options.messages);

        // Convert messages to API format
        const apiMessages = messages.map((msg) => {
            const apiMsg: Record<string, unknown> = {
                role: msg.role,
            };

            // Handle content - string or array of content blocks
            if (typeof msg.content === 'string') {
                apiMsg.content = msg.content;
            } else {
                // Array of content blocks
                apiMsg.content = msg.content;
            }

            // Add tool_call_id for tool messages
            if (msg.tool_call_id) {
                apiMsg.tool_call_id = msg.tool_call_id;
            }

            return apiMsg;
        });

        const payload: Record<string, unknown> = {
            model: options.model,
            messages: apiMessages,
        };

        // Add optional parameters
        if (options.temperature !== undefined) {
            payload.temperature = options.temperature;
        }
        if (options.topP !== undefined) {
            payload.top_p = options.topP;
        }
        if (options.maxTokens !== undefined) {
            payload.max_tokens = options.maxTokens;
        }

        // Add tools if provided
        if (options.tools && options.tools.length > 0) {
            payload.tools = options.tools.map((tool) => ({
                type: tool.type,
                function: {
                    name: tool.function.name,
                    description: tool.function.description,
                    parameters: tool.function.parameters,
                },
            }));
        }

        // Add tool_choice if provided
        if (options.toolChoice !== undefined) {
            if (typeof options.toolChoice === 'string') {
                payload.tool_choice = options.toolChoice;
            } else {
                // Specific tool choice
                payload.tool_choice = {
                    type: options.toolChoice.type,
                    function: { name: options.toolChoice.function.name },
                };
            }
        }

        // Add guardrails if provided
        if (options.guardrails) {
            payload.guardrails = {
                enabled: options.guardrails.enabled,
            };
            if (options.guardrails.responseWhenUnsafe) {
                (
                    payload.guardrails as Record<string, unknown>
                ).response_when_unsafe = options.guardrails.responseWhenUnsafe;
            }
        }

        // Add stream flag - must explicitly set false for non-streaming
        payload.stream = stream;
        if (stream) {
            // Include usage in stream for final chunk
            payload.stream_options = { include_usage: true };
        }

        return payload;
    }

    /**
     * Creates sanitized request info for debugging (no auth token)
     */
    private createRequestInfo(
        url: string,
        headers: Record<string, string>,
        payload: unknown,
    ): CortexCompleteRequestInfo {
        // Remove Authorization header for security
        const sanitizedHeaders = { ...headers };
        delete sanitizedHeaders.Authorization;

        return {
            url,
            headers: sanitizedHeaders,
            payload,
        };
    }

    /**
     * Parses the API response into our CortexChoice format
     */
    private parseChoices(apiChoices: unknown[]): CortexChoice[] {
        return apiChoices.map((choice: unknown) => {
            const c = choice as Record<string, unknown>;
            const message = c.message as Record<string, unknown>;

            const choiceMessage: CortexChoiceMessage = {
                role: 'assistant',
                content: (message.content as string) || null,
            };

            // Parse tool calls if present
            if (message.tool_calls && Array.isArray(message.tool_calls)) {
                choiceMessage.toolCalls = (
                    message.tool_calls as Record<string, unknown>[]
                ).map((tc) => ({
                    id: tc.id as string,
                    type: 'function' as const,
                    function: {
                        name: (tc.function as Record<string, unknown>)
                            .name as string,
                        arguments: (tc.function as Record<string, unknown>)
                            .arguments as string,
                    },
                }));
            }

            return {
                index: c.index as number,
                message: choiceMessage,
                finishReason:
                    (c.finish_reason as CortexChoice['finishReason']) || 'stop',
            };
        });
    }

    /**
     * Parses token usage from API response
     */
    private parseUsage(apiUsage: unknown): CortexTokenUsage | undefined {
        if (!apiUsage) return undefined;

        const usage = apiUsage as Record<string, unknown>;
        return {
            promptTokens: (usage.prompt_tokens as number) || 0,
            completionTokens: (usage.completion_tokens as number) || 0,
            totalTokens: (usage.total_tokens as number) || 0,
            promptTokensCached: usage.prompt_tokens_cached as
                | number
                | undefined,
        };
    }

    /**
     * Generates text completion using Snowflake Cortex LLM (non-streaming)
     */
    async cortexComplete(
        options: CortexCompleteOptions,
        config_name?: string,
    ): Promise<CortexCompleteResponse> {
        const cfg = this.cfg(config_name);

        const url = `${cfg.accessUrl}/api/v2/cortex/inference:complete`;
        const payload = this.buildCortexCompletePayload(options, false);
        const timeout = options.timeout ?? 120000;

        const headers: Record<string, string> = {
            Authorization: `Bearer ${cfg.token}`,
            'Content-Type': 'application/json',
            Accept: 'application/json',
        };

        // Add region header if specified
        const regionHeader = this.getRegionHeader(options.region);
        if (regionHeader) {
            headers['X-Snowflake-Cortex-Region'] = regionHeader;
        }

        const requestInfo = this.createRequestInfo(url, headers, payload);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
                signal: AbortSignal.timeout(timeout),
            });

            if (!response.ok) {
                const errorText = await response.text();
                return {
                    success: false,
                    error: `HTTP ${response.status}: ${errorText}`,
                    statusCode: response.status,
                    request: requestInfo,
                };
            }

            const data = (await response.json()) as Record<string, unknown>;

            return {
                success: true,
                id: data.id as string | undefined,
                model: data.model as string | undefined,
                choices: this.parseChoices((data.choices as unknown[]) || []),
                usage: this.parseUsage(data.usage),
                statusCode: response.status,
                request: requestInfo,
            };
        } catch (error) {
            const errorMessage =
                error instanceof Error ? error.message : String(error);

            // Check for timeout
            if (
                errorMessage.includes('abort') ||
                errorMessage.includes('timeout')
            ) {
                return {
                    success: false,
                    error: `Request timeout after ${timeout}ms`,
                    statusCode: 0,
                    request: requestInfo,
                };
            }

            return {
                success: false,
                error: `Request failed: ${errorMessage}`,
                statusCode: 0,
                request: requestInfo,
            };
        }
    }

    /**
     * Generates streaming text completion using Snowflake Cortex LLM
     * Returns an async iterable that yields chunks as they arrive
     */
    async *cortexCompleteStream(
        options: CortexCompleteOptions,
        config_name?: string,
    ): AsyncIterable<CortexStreamChunk> {
        const cfg = this.cfg(config_name);

        const url = `${cfg.accessUrl}/api/v2/cortex/inference:complete`;
        const payload = this.buildCortexCompletePayload(options, true);
        const timeout = options.timeout ?? 120000;

        const headers: Record<string, string> = {
            Authorization: `Bearer ${cfg.token}`,
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
        };

        // Add region header if specified
        const regionHeader = this.getRegionHeader(options.region);
        if (regionHeader) {
            headers['X-Snowflake-Cortex-Region'] = regionHeader;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload),
            signal: AbortSignal.timeout(timeout),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        if (!response.body) {
            throw new Error('No response body received');
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

                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6).trim();

                        if (dataStr === '[DONE]') {
                            return;
                        }

                        try {
                            const eventData = JSON.parse(dataStr) as Record<
                                string,
                                unknown
                            >;
                            const chunk = this.parseStreamChunk(eventData);
                            yield chunk;
                        } catch {
                            // Skip malformed JSON lines
                            console.warn(
                                `[SDK] Failed to parse stream chunk: ${dataStr}`,
                            );
                        }
                    }
                }
            }

            // Process any remaining buffer
            if (buffer.trim()) {
                if (buffer.startsWith('data: ')) {
                    const dataStr = buffer.substring(6).trim();
                    if (dataStr && dataStr !== '[DONE]') {
                        try {
                            const eventData = JSON.parse(dataStr) as Record<
                                string,
                                unknown
                            >;
                            const chunk = this.parseStreamChunk(eventData);
                            yield chunk;
                        } catch {
                            // Skip malformed JSON
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    /**
     * Parses a streaming chunk from the API response
     */
    private parseStreamChunk(data: Record<string, unknown>): CortexStreamChunk {
        const choices = (data.choices as Record<string, unknown>[]) || [];

        const parsedChoices: CortexStreamChoice[] = choices.map((choice) => {
            const delta = (choice.delta as Record<string, unknown>) || {};

            const parsedDelta: CortexStreamDelta = {};

            if (delta.role) {
                parsedDelta.role = delta.role as 'assistant';
            }
            if (delta.content !== undefined) {
                parsedDelta.content = delta.content as string;
            }

            // Parse tool calls delta
            if (delta.tool_calls && Array.isArray(delta.tool_calls)) {
                parsedDelta.toolCalls = (
                    delta.tool_calls as Record<string, unknown>[]
                ).map((tc): CortexStreamDeltaToolCall => {
                    const result: CortexStreamDeltaToolCall = {
                        index: tc.index as number,
                    };
                    if (tc.id) result.id = tc.id as string;
                    if (tc.type) result.type = tc.type as 'function';
                    if (tc.function) {
                        const fn = tc.function as Record<string, unknown>;
                        result.function = {};
                        if (fn.name) result.function.name = fn.name as string;
                        if (fn.arguments)
                            result.function.arguments = fn.arguments as string;
                    }
                    return result;
                });
            }

            return {
                index: (choice.index as number) || 0,
                delta: parsedDelta,
                finishReason:
                    (choice.finish_reason as CortexStreamChoice['finishReason']) ||
                    null,
            };
        });

        return {
            id: (data.id as string) || '',
            object: 'chat.completion.chunk',
            created: (data.created as number) || Math.floor(Date.now() / 1000),
            model: (data.model as string) || '',
            choices: parsedChoices,
            usage: this.parseUsage(data.usage),
        };
    }

    /**
     * Executes another workflow as a subworkflow
     */
    async executeSubworkflow(
        options: SubworkflowOptions,
        config_name?: string,
    ): Promise<SubworkflowResponse> {
        // Validate that exactly one of workflowId or workflowName is provided
        const hasId =
            options.workflowId !== undefined && options.workflowId !== '';
        const hasName =
            options.workflowName !== undefined && options.workflowName !== '';

        if (hasId === hasName) {
            if (hasId) {
                return {
                    success: false,
                    error: 'Provide either workflowId or workflowName, not both',
                };
            } else {
                return {
                    success: false,
                    error: 'Either workflowId or workflowName is required',
                };
            }
        }

        const cfg = this.cfg(config_name);

        const token = cfg.token;

        // In SPCS, the runner job container is separate from controld — use the
        // controld internal DNS passed via P67_CONTROLD_URL. In local/Docker mode,
        // the workflow is a child process of controld so localhost works.
        const controldUrl = process.env.P67_CONTROLD_URL;
        const port = process.env.PORT || '3002';
        const accessUrl = controldUrl || `http://localhost:${port}`;

        if (!token) {
            return {
                success: false,
                error: 'token is required in config for subworkflow execution',
            };
        }

        // Build URL based on whether we're using ID or name.
        // Always use sync=true for subworkflow calls — the runner
        // needs the complete result, not an async 202 response.
        let url: string;
        if (hasId) {
            url = `${accessUrl}/api/workflow/${encodeURIComponent(options.workflowId ?? '')}/run?sync=true`;
        } else {
            url = `${accessUrl}/api/workflow/name/${encodeURIComponent(options.workflowName ?? '')}/run?sync=true`;
        }

        // Build request body with params
        const payload: { params?: Record<string, string> } = {};
        if (options.params) {
            payload.params = options.params;
        }

        const timeout = options.timeout ?? 300000; // 5 minutes default

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    // SPCS ingress injects this header for external requests;
                    // for internal service-to-service calls we must set it
                    // ourselves so controld's user plugin can resolve the user.
                    ...(cfg.username
                        ? { 'sf-context-current-user': cfg.username }
                        : {}),
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                let errorMsg: string;
                try {
                    const errorData = (await response.json()) as {
                        message?: string;
                        error?: string;
                    };
                    errorMsg =
                        errorData.message ||
                        errorData.error ||
                        `HTTP ${response.status}`;
                } catch {
                    errorMsg = `HTTP ${response.status}: ${response.statusText}`;
                }
                return {
                    success: false,
                    error: errorMsg,
                };
            }

            const data = (await response.json()) as {
                success?: boolean;
                exitCode?: number;
                stdout?: string[];
                stderr?: string[];
                status?: 'completed' | 'failed' | 'interrupted';
                runId?: string;
                result?: unknown;
            };

            return {
                success: data.success ?? false,
                exitCode: data.exitCode,
                stdout: data.stdout,
                stderr: data.stderr,
                status: data.status,
                runId: data.runId,
                result: data.result,
            };
        } catch (err) {
            if (err instanceof Error && err.name === 'AbortError') {
                return {
                    success: false,
                    error: `Request timed out after ${timeout}ms`,
                };
            }
            return {
                success: false,
                error: err instanceof Error ? err.message : String(err),
            };
        }
    }

    /**
     * Invokes the Cortex Code CLI as a subprocess
     */
    async cortexCode(options: CortexCodeOptions): Promise<CortexCodeResponse> {
        const {
            prompt,
            timeout = 900,
            workDir,
            model,
            allowAllToolCalls,
        } = options;

        if (!prompt) {
            return {
                success: false,
                output: '',
                error: 'prompt is required',
            };
        }

        const args = ['-p', prompt, '--bypass'];

        if (model) {
            args.push('--model', model);
        }

        if (allowAllToolCalls) {
            args.push('--dangerously-allow-all-tool-calls');
        }

        // Write a temporary connections.toml so the cortex CLI can authenticate
        let snowflakeHome: string | undefined;
        try {
            const cfg = this.cfg();
            if (cfg.account && (cfg.token || cfg.password)) {
                snowflakeHome = fs.mkdtempSync(
                    path.join(os.tmpdir(), 'p67-cortex-'),
                );
                const lines: string[] = [
                    'default_connection_name = "default"',
                    '',
                    '[connections.default]',
                ];
                if (cfg.account) lines.push(`account = "${cfg.account}"`);
                if (cfg.username) lines.push(`user = "${cfg.username}"`);
                if (cfg.token) {
                    lines.push('authenticator = "programmatic_access_token"');
                    lines.push(`token = "${cfg.token}"`);
                } else if (cfg.password) {
                    lines.push(`password = "${cfg.password}"`);
                }
                if (cfg.accessUrl)
                    lines.push(
                        `host = "${cfg.accessUrl.replace(/^https?:\/\//, '')}"`,
                    );
                if (cfg.warehouse) lines.push(`warehouse = "${cfg.warehouse}"`);
                if (cfg.database) lines.push(`database = "${cfg.database}"`);
                if (cfg.schema) lines.push(`schema = "${cfg.schema}"`);
                lines.push('');
                fs.writeFileSync(
                    path.join(snowflakeHome, 'config.toml'),
                    lines.join('\n'),
                    { mode: 0o600 },
                );
            }
        } catch {
            // If we can't build a connections file, proceed without one —
            // cortex will report the missing-connection error itself.
        }

        try {
            return await new Promise<CortexCodeResponse>((resolve) => {
                const child = child_process.execFile(
                    'cortex',
                    args,
                    {
                        cwd: workDir,
                        timeout: timeout * 1000,
                        maxBuffer: 50 * 1024 * 1024, // 50 MB
                        env: {
                            ...process.env,
                            ...(snowflakeHome
                                ? { SNOWFLAKE_HOME: snowflakeHome }
                                : {}),
                        },
                    },
                    (error, stdout, stderr) => {
                        if (error) {
                            // Timeout
                            if (
                                error.killed ||
                                error.message.includes('TIMEOUT')
                            ) {
                                resolve({
                                    success: false,
                                    output: '',
                                    error: `Cortex Code timed out after ${timeout} seconds`,
                                    exitCode: error.code
                                        ? Number(error.code)
                                        : undefined,
                                });
                                return;
                            }

                            // Non-zero exit
                            const errorMsg =
                                stderr.trim() ||
                                stdout.trim() ||
                                `cortex exited with code ${error.code}`;
                            resolve({
                                success: false,
                                output: stdout,
                                error: errorMsg,
                                exitCode: error.code
                                    ? Number(error.code)
                                    : undefined,
                            });
                            return;
                        }

                        resolve({
                            success: true,
                            output: stdout,
                            exitCode: 0,
                        });
                    },
                );

                // Handle spawn errors (e.g., cortex not found)
                child.on('error', (err) => {
                    resolve({
                        success: false,
                        output: '',
                        error: err.message.includes('ENOENT')
                            ? 'The cortex CLI is not installed or not in PATH.'
                            : `Failed to spawn cortex: ${err.message}`,
                    });
                });
            });
        } catch (error) {
            return {
                success: false,
                output: '',
                error: `Unexpected error: ${error instanceof Error ? error.message : String(error)}`,
            };
        } finally {
            // Clean up the temporary connections file
            if (snowflakeHome) {
                try {
                    fs.rmSync(snowflakeHome, { recursive: true, force: true });
                } catch {
                    // Ignore cleanup errors
                }
            }
        }
    }
}

function validateConfig(config: P67ConfigValue): P67ConfigValue {
    // Patch config and fix accessURL if it's missing
    if (!config.accessUrl) {
        if (config.account) {
            const accountLocator = config.account.toLowerCase();
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
            for (const [key, value] of Object.entries(c.parameters)) {
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

/**
 * Create a WorkflowSDK instance with OAuth support
 */
export function createWorkflowSDK(
    config: P67Config,
    valueManager: ValueManager,
): WorkflowSDK {
    return new WorkflowSDKImpl({
        config,
        oauthTokenResolver: (oauthRef: string) =>
            valueManager.getOAuthToken(oauthRef),
    });
}
