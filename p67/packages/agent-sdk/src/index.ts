/**
 * @preserve
 * @p67/agent-sdk
 *
 * Agent SDK for P67 platform
 * Provides utilities for workflows to interact with the real world (namely, Snowflake and Cortex services)
 */

export const version = '0.1.0';

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
 * P67 Agent SDK Client
 * Encapsulates all API functions for interacting with Snowflake and Cortex services
 *
 * Configuration is loaded from /tmp/config as JSON with the following structure:
 * {
 *   "snowflakeConfig": {
 *     "account": "string (required)",
 *     "username": "string (required)",
 *     "authenticator": "string (optional - auto-set based on token/password)",
 *     "accessUrl": "string (optional - auto-generated from account)",
 *     "token": "string (optional - required for token auth)",
 *     "password": "string (optional - required for password auth)",
 *     "warehouse": "string (optional)",
 *     "database": "string (optional)",
 *     "schema": "string (optional)"
 *   }
 * }
 *
 * Note: Either token or password must be provided (but not both).
 *       If authenticator is not provided, it will be auto-set to:
 *       - "PROGRAMMATIC_ACCESS_TOKEN" if token is provided
 *       - "PASSWORD" if password is provided
 *       If accessUrl is not provided, it will be generated from the account.
 *
 * @example
 * // Create client instance (reads config from /tmp/config)
 * const sdk = new AgentSDK();
 *
 * // Execute queries
 * const result = await sdk.executeQueryReadOnly('SELECT * FROM my_table');
 *
 * // Query Cortex Analyst
 * const analystResponse = await sdk.queryCortexAnalyst('What were sales last month?');
 *
 * // Call Cortex Agent
 * const agentResponse = await sdk.callCortexAgent('Hello', {
 *   agentDatabase: 'DB',
 *   agentSchema: 'SCHEMA',
 *   agentName: 'my_agent'
 * });
 *
 * // Cleanup when done
 * await sdk.close();
 */
export interface AgentSDK {
  /**
   * Executes a read-only SELECT query against Snowflake
   * Validates that the query is read-only before execution
   * Rejects DML and DDL statements for safety
   *
   * @param {string} query - SQL SELECT query to execute
   * @returns {Promise<QueryResult>} Query results with statement and rows
   * @throws {Error} If query is not read-only or execution fails
   *
   * @example
   * const sdk = new AgentSDK();
   * const result = await sdk.executeQueryReadOnly('SELECT * FROM my_table LIMIT 10');
   * console.log(result.rows);
   */
  executeQueryReadOnly(query: string, config_name?: string): Promise<QueryResult>;

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
   * const sdk = new AgentSDK();
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
  queryCortexAnalyst(
    question: string,
    semanticModel?: string,
    config_name?: string,
  ): Promise<CortexAnalystResponse>;

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
   * const sdk = new AgentSDK();
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
  callCortexAgent(
    question: string,
    options?: CortexAgentOptions,
    config_name?: string,
  ): Promise<CortexAgentResponse>;

  /**
   * Closes the cached Snowflake connection
   * Call this when shutting down to properly cleanup resources
   *
   * @returns {Promise<void>}
   *
   * @example
   * const sdk = new AgentSDK();
   * // ... use sdk ...
   * await sdk.close();
   */
  close(): Promise<void>;
}
