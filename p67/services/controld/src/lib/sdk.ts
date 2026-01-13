/**
 * @preserve
 * @p67/agent-sdk
 *
 * Agent SDK for P67 platform
 * Provides utilities for workflows to interact with the real world (namely, Snowflake and Cortex services)
 */

import { z } from 'zod';

export const version = '0.1.0';

export const P67ConfigValueSchema = z.object({
    account: z.string().optional(),
    username: z.string().optional(),
    authenticator: z.string().optional(),
    accessUrl: z.string().optional(),
    token: z.string().optional(),
    password: z.string().optional(),
    warehouse: z.string().optional(),
    database: z.string().optional(),
    schema: z.string().optional(),
    email_integration: z.string().optional(),
});

export type P67ConfigValue = z.infer<typeof P67ConfigValueSchema>;

/**
 * P67 configuration schema
 *
 * The core configuration mechanism of the P67 platform.
 */
export const P67ConfigSchema = z.object({
    snowflakeConfig: z.map(z.string(), P67ConfigValueSchema),
});

export type P67Config = z.infer<typeof P67ConfigSchema>;

/**
 * Query execution result
 */
export interface QueryResult {
    statement: unknown;
    rows: unknown[];
}

/**
 * Cortex Analyst API response
 */
export interface CortexAnalystResponse {
    success: boolean;
    data?: unknown;
    error?: string;
}

/**
 * Cortex Agent API response with detailed debugging information
 */
export interface CortexAgentResponse {
    success: boolean;
    status_code: number;
    data?: unknown;
    error?: string;
    request?: {
        url: string;
        headers: Record<string, string>;
        payload: unknown;
    };
    response?: {
        status_code: number;
        headers: Record<string, string>;
    };
}

/**
 * Agent stream event
 */
export interface AgentStreamEvent {
    eventName: string;
    data: unknown;
}

/**
 * Options for calling Cortex Agent
 */
export interface CortexAgentOptions {
    agentDatabase?: string;
    agentSchema?: string;
    agentName?: string;
    parentMessageId?: string;
    onStream?: (event: AgentStreamEvent) => void;
}

/**
 * Snowflake statement binds
 */
export type Bind = string | number | boolean | null;
export type Binds = Bind[];

/**
 * Snowflake statement
 */
export interface SnowflakeStatement {
    sqlText: string;
    binds?: Binds;
}

export interface EmailOptions {
    email_addresses: [string];
    subject: string;
    body: string;
    content_type?: string;
    integration_name?: string;
}

/**
 * Interface for the P67 Agent SDK
 * Defines the public API for interacting with Snowflake and Cortex services
 */
export interface AgentSDK {
    /**
     * Executes a read-only SELECT query against Snowflake
     *
     * Validates that the query is read-only before execution.
     * Allows SELECT, WITH (CTE), SHOW, and DESCRIBE statements.
     * Rejects DML (INSERT, UPDATE, DELETE) and DDL (CREATE, ALTER, DROP) statements for safety.
     *
     * @param query - SQL SELECT query to execute
     * @param config_name - Optional name of the Snowflake config to use. If not provided and only
     *                      one config exists, that config will be used automatically.
     * @returns Query results containing the statement metadata and result rows
     * @throws Error if the query is not read-only, contains multiple statements, or execution fails
     *
     * @example
     * const result = await sdk.executeQueryReadOnly('SELECT * FROM my_table LIMIT 10');
     * console.log(result.rows);
     *
     * @example
     * // Using a specific config
     * const result = await sdk.executeQueryReadOnly(
     *   'SELECT COUNT(*) FROM orders',
     *   'production_config'
     * );
     */
    executeQueryReadOnly(
        stmt: SnowflakeStatement,
        config_name?: string,
    ): Promise<QueryResult>;

    /**
     * Queries Cortex Analyst with a natural language question
     *
     * Uses the Snowflake Cortex Analyst API to convert natural language questions
     * into SQL queries and execute them against your semantic model.
     *
     * @param question - Natural language question to ask (e.g., "What were sales last month?")
     * @param semanticModel - Path to semantic model file (stage path like `@my_stage/model.yaml`).
     *                        Defaults to `CORTEX_ANALYST_SEMANTIC_MODEL` environment variable if not provided.
     * @param config_name - Optional name of the Snowflake config to use. If not provided and only
     *                      one config exists, that config will be used automatically.
     * @returns Response object with `success` boolean, `data` on success, or `error` message on failure.
     *          Never throws - errors are returned in the response object.
     *
     * @example
     * const response = await sdk.queryCortexAnalyst(
     *   'What were the top 5 products by revenue last month?',
     *   '@my_stage/semantic_model.yaml'
     * );
     *
     * if (response.success) {
     *   console.log(response.data);
     * } else {
     *   console.error(response.error);
     * }
     */
    queryCortexAnalyst(
        question: string,
        semanticModel?: string,
        config_name?: string,
    ): Promise<CortexAnalystResponse>;

    /**
     * Calls a Cortex Agent with a question and streams the response
     *
     * Sends a message to a Snowflake Cortex Agent and processes the streaming response.
     * Supports conversational context via `parentMessageId` for multi-turn conversations.
     *
     * @param question - Question or message to send to the agent
     * @param options - Configuration options for the agent call:
     *   - `agentDatabase`: Database containing the agent (defaults to config database)
     *   - `agentSchema`: Schema containing the agent (defaults to config schema)
     *   - `agentName`: Name of the agent (required)
     *   - `parentMessageId`: Parent message ID for conversation continuity (defaults to '0' for new conversations)
     *   - `onStream`: Callback function invoked for each streaming event, receives `{ eventName, data }`
     * @param config_name - Optional name of the Snowflake config to use. If not provided and only
     *                      one config exists, that config will be used automatically.
     * @returns Response object with `success` boolean, `status_code`, `data` on success,
     *          `error` on failure, and `request` debugging info. Never throws - errors are
     *          returned in the response object.
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
     *
     * @example
     * // Multi-turn conversation
     * const firstResponse = await sdk.callCortexAgent('Hello', { agentName: 'my_agent' });
     * const secondResponse = await sdk.callCortexAgent('Tell me more', {
     *   agentName: 'my_agent',
     *   parentMessageId: firstResponse.data?.messageId
     * });
     */
    callCortexAgent(
        question: string,
        options?: CortexAgentOptions,
        config_name?: string,
    ): Promise<CortexAgentResponse>;

    /**
     * Sends an email using the Snowflake Email Integration
     *
     * @param email_addresses - Array of email addresses to send the email to
     * @param subject - Subject of the email
     * @param body - Body of the email
     * @param content_type - Content type of the email
     * @param integration_name - Name of the email integration to use. If not provided, the default email integration will be used.
     * @returns Promise that resolves to true if the email is sent successfully, false otherwise
     */
    email(options: EmailOptions, config_name?: string): Promise<boolean>;

    /**
     * Closes the cached Snowflake connection
     *
     * Call this method when shutting down your application to properly cleanup resources
     * and release the connection back to the pool. Safe to call multiple times.
     *
     * @returns Promise that resolves when the connection is closed
     *
     * @example
     * try {
     *   const result = await sdk.executeQueryReadOnly('SELECT * FROM my_table');
     *   // ... process result ...
     * } finally {
     *   await sdk.close();
     * }
     */
    close(): Promise<void>;
}
