/**
 * @preserve
 * @p67/agent-sdk
 *
 * Agent SDK for P67 platform
 * Provides utilities for workflows to interact with the real world (namely, Snowflake and Cortex services)
 */

export const version = '0.1.0';

import snowflake from 'snowflake-sdk';
import { z } from 'zod';

const P67ConfigValueSchema = z.object({
  account: z.string().optional(),
  username: z.string().optional(),
  authenticator: z.string().optional(),
  accessUrl: z.string().optional(),
  token: z.string().optional(),
  password: z.string().optional(),
  warehouse: z.string().optional(),
  database: z.string().optional(),
  schema: z.string().optional(),
});

export type P67ConfigValue = z.infer<typeof P67ConfigValueSchema>;


/**
 * P67 configuration schema
 * 
 * The core configuration mechanism of the P67 platform.
 */
const P67ConfigSchema = z.object({
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
export class AgentSDK {
  private cachedConnection: snowflake.Connection | null = null;
  private isConnecting = false;
  private connectionPromise: Promise<snowflake.Connection> | null = null;
  private config: z.infer<typeof P67ConfigSchema>;

  constructor(config: P67Config) {
    // Validate that at least one config exists
    if (config.snowflakeConfig.size === 0) {
      throw new Error('No Snowflake configurations provided');
    }

    // Validate and process each config entry
    const validatedConfig = new Map<string, P67ConfigValue>();

    for (const [name, cfg] of config.snowflakeConfig.entries()) {
      // Validate schema
      const parseResult = P67ConfigValueSchema.safeParse(cfg);
      if (!parseResult.success) {
        throw new Error('Invalid config format: config does not match expected schema');
      }

      const validatedCfg = parseResult.data;

      // Validate required fields
      if (!validatedCfg.account) {
        throw new Error('Invalid config format: account is required');
      }

      // Check that both token and password are not set
      if (validatedCfg.token && validatedCfg.password) {
        throw new Error('Both "token" and "password" are set in config');
      }

      // Check that at least one of token or password is set
      if (!validatedCfg.token && !validatedCfg.password) {
        throw new Error('Missing authenticator: config requires either token or password');
      }

      // Auto-set authenticator based on token/password if not provided
      if (!validatedCfg.authenticator) {
        if (validatedCfg.token) {
          validatedCfg.authenticator = 'PROGRAMMATIC_ACCESS_TOKEN';
        } else if (validatedCfg.password) {
          validatedCfg.authenticator = 'PASSWORD';
        }
      }

      // Auto-generate accessUrl from account if not provided
      if (!validatedCfg.accessUrl) {
        const accountLower = validatedCfg.account.toLowerCase();
        validatedCfg.accessUrl = `https://${accountLower}.snowflakecomputing.com`;
      }

      validatedConfig.set(name, validatedCfg);
    }

    this.config = { snowflakeConfig: validatedConfig };
  }

  private getSnowflakeConnectionOptions(cfg: P67ConfigValue): snowflake.ConnectionOptions {
    return {
      account: cfg.account,
      username: cfg.username,
      authenticator: cfg.authenticator,
      accessUrl: cfg.accessUrl,
      token: cfg.token,
      password: cfg.password,
      warehouse: cfg.warehouse,
      database: cfg.database,
      schema: cfg.schema,
    };
  }

  private cfg(config_name?: string): P67ConfigValue {
    if (config_name) {
      if (!this.config.snowflakeConfig.has(config_name)) {
        throw new Error(`Config ${config_name} not found`);
      }
      return P67ConfigValueSchema.parse(this.config.snowflakeConfig.get(config_name));
    }
    // Get the only one if it exists
    if (this.config.snowflakeConfig.size === 0) {
      throw new Error('No Snowflake configurations available');
    }
    if (this.config.snowflakeConfig.size === 1) {
      return P67ConfigValueSchema.parse(this.config.snowflakeConfig.values().next().value);
    }
    throw new Error('Multiple Snowflake configs found, but no config name provided');
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
        this.cachedConnection!.execute({
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
   * Uses configuration loaded from /tmp/config file
   * @returns {Promise<snowflake.Connection>} Connected Snowflake connection
   * @throws {Error} If required configuration values are missing or connection fails
   */
  private async getSnowflakeConnection(config_name?: string): Promise<snowflake.Connection> {
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
      const connection = snowflake.createConnection(this.getSnowflakeConnectionOptions(cfg));

      connection.connect((err, conn) => {
        this.isConnecting = false;

        if (err) {
          this.cachedConnection = null;
          this.connectionPromise = null;
          reject(new Error(`Failed to connect to Snowflake: ${err.message}`));
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
   * @param {string} query - SQL query to execute
   * @returns {Promise<QueryResult>} Query results with statement and rows
   * @throws {Error} If query execution fails
   */
  private async executeQuery(query: string, config_name?: string): Promise<QueryResult> {
    const conn = await this.getSnowflakeConnection(config_name);

    return new Promise((resolve, reject) => {
      conn.execute({
        sqlText: query,
        complete: (err, stmt, rows) => {
          if (err) {
            reject(new Error(`Query execution failed: ${err.message}`));
          } else {
            resolve({ statement: stmt, rows: rows || [] });
          }
        },
      });
    });
  }

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
  async executeQueryReadOnly(query: string, config_name?: string): Promise<QueryResult> {
    if (!this.isSelectQuery(query)) {
      throw new Error(
        'Only SELECT queries are allowed. DML (INSERT, UPDATE, DELETE) and DDL (CREATE, ALTER, DROP) statements are not permitted.',
      );
    }
    return this.executeQuery(query, config_name);
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
  async queryCortexAnalyst(
    question: string,
    semanticModel?: string,
    config_name?: string,
  ): Promise<CortexAnalystResponse> {
    const cfg = this.cfg(config_name);
    try {
      const model = semanticModel || process.env.CORTEX_ANALYST_SEMANTIC_MODEL;

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
        throw new Error('AGENT_DATABASE is required via configuration or options');
      }

      if (!schema) {
        throw new Error('AGENT_SCHEMA is required via configuration or options');
      }

      if (!name) {
        throw new Error('AGENT_NAME is required via options');
      }

      const token = cfg.token;
      if (!token) {
        throw new Error('SNOWFLAKE_TOKEN is required in configuration');
      }

      if (token === 'undefined' || !token.trim()) {
        throw new Error('SNOWFLAKE_TOKEN must be a valid token, not empty or undefined');
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
                  onStream({ eventName: currentEventName, data: eventData });
                }

                if (currentEventName === 'response' && eventData.content) {
                  finalMessage = eventData;
                }
              } catch {
                continue;
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
  async close(): Promise<void> {
    if (this.cachedConnection) {
      return new Promise((resolve) => {
        this.cachedConnection!.destroy((err) => {
          if (err) {
            console.error('Error closing connection:', err.message);
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
