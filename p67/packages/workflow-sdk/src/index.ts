/**
 * @preserve
 * @p67/workflow-sdk
 *
 * Workflow SDK for P67 platform
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
    parameters: z.record(z.string(), z.string()).optional(),
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
 * HTTP request options for external API calls
 */
export interface HttpRequestOptions {
    /** The URL to request */
    url: string;
    /** HTTP method (defaults to GET) */
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD';
    /** Request headers */
    headers?: Record<string, string>;
    /** Request body (will be JSON serialized if object) */
    body?: unknown;
    /** OAuth secret reference for automatic Bearer token injection */
    oauthRef?: string;
    /** Request timeout in milliseconds (default 30000) */
    timeout?: number;
}

/**
 * HTTP response from external API call
 */
export interface HttpResponse {
    /** Whether the request succeeded (2xx status) */
    success: boolean;
    /** HTTP status code */
    status: number;
    /** Response headers */
    headers: Record<string, string>;
    /** Response body (parsed as JSON if content-type is application/json) */
    data?: unknown;
    /** Error message if request failed */
    error?: string;
}

// ============================================================================
// Slack Block Kit Types (subset for interrupt notifications)
// ============================================================================

/**
 * Slack text object
 */
export interface SlackTextObject {
    type: 'plain_text' | 'mrkdwn';
    text: string;
    emoji?: boolean;
}

/**
 * Slack button element
 */
export interface SlackButtonElement {
    type: 'button';
    text: { type: 'plain_text'; text: string; emoji?: boolean };
    action_id?: string;
    value?: string;
    style?: 'primary' | 'danger';
    url?: string;
}

/**
 * Slack header block
 */
export interface SlackHeaderBlock {
    type: 'header';
    text: { type: 'plain_text'; text: string; emoji?: boolean };
    block_id?: string;
}

/**
 * Slack section block
 */
export interface SlackSectionBlock {
    type: 'section';
    text?: SlackTextObject;
    fields?: SlackTextObject[];
    accessory?: SlackButtonElement;
    block_id?: string;
}

/**
 * Slack divider block
 */
export interface SlackDividerBlock {
    type: 'divider';
    block_id?: string;
}

/**
 * Slack actions block (contains interactive elements)
 */
export interface SlackActionsBlock {
    type: 'actions';
    elements: SlackButtonElement[];
    block_id?: string;
}

/**
 * Slack context block
 */
export interface SlackContextBlock {
    type: 'context';
    elements: Array<
        SlackTextObject | { type: 'image'; image_url: string; alt_text: string }
    >;
    block_id?: string;
}

/**
 * Slack image block
 */
export interface SlackImageBlock {
    type: 'image';
    image_url: string;
    alt_text: string;
    title?: { type: 'plain_text'; text: string };
    block_id?: string;
}

/**
 * Union type for all supported Slack blocks
 */
export type SlackBlock =
    | SlackHeaderBlock
    | SlackSectionBlock
    | SlackDividerBlock
    | SlackActionsBlock
    | SlackContextBlock
    | SlackImageBlock;

// ============================================================================
// Interrupt Notification Types
// ============================================================================

/**
 * Simple button configuration for interrupt notifications
 */
export interface InterruptButton {
    /** Button label text */
    label: string;
    /** Value returned when button is clicked */
    value: string;
    /** Button style */
    style?: 'primary' | 'danger';
}

/**
 * Preset button configurations
 */
export type ButtonPreset = 'approve_reject' | 'yes_no' | 'continue_cancel';

/**
 * Slack notification configuration for interrupts
 */
export interface SlackNotifyConfig {
    type: 'slack';
    /** OAuth token reference (from p67 oauth connect) */
    oauthRef: string;
    /** Recipient: 'self' for DM to token owner, or user/channel ID */
    recipient?: 'self' | string;
    /** Simple text message (supports Slack mrkdwn) */
    text?: string;
    /** Simple button configuration */
    buttons?: InterruptButton[];
    /** Use a preset button configuration */
    buttonPreset?: ButtonPreset;
    /** Full Block Kit blocks for complete control */
    blocks?: SlackBlock[];
}

/**
 * Union type for all notification configurations (extensible for future channels)
 */
export type NotifyConfig = SlackNotifyConfig;

/**
 * Options for interrupt calls
 */
export interface InterruptOptions {
    /** Optional timeout in ms (default: no timeout - waits indefinitely) */
    timeout?: number;
    /** Optional node identifier for debugging */
    nodeId?: string;
    /** Optional notification configuration (e.g., send Slack message) */
    notify?: NotifyConfig;
}

/**
 * Interrupt payload that surfaces to the caller
 */
export interface InterruptPayload<T = unknown> {
    /** Unique identifier for this interrupt */
    interruptId: string;
    /** The value passed to interrupt() */
    value: T;
    /** When the interrupt was triggered */
    timestamp: string;
    /** Optional node identifier */
    nodeId?: string;
}

// ============================================================================
// Subworkflow Types
// ============================================================================

/**
 * Options for executing a subworkflow
 */
export interface SubworkflowOptions {
    /** Run workflow by ID (mutually exclusive with workflowName) */
    workflowId?: string;
    /** Run workflow by name - uses latest version (mutually exclusive with workflowId) */
    workflowName?: string;
    /** Runtime parameter overrides */
    params?: Record<string, string>;
    /** Timeout in milliseconds (default: 300000 = 5 min) */
    timeout?: number;
}

/**
 * Response from subworkflow execution
 */
export interface SubworkflowResponse {
    /** Whether the subworkflow completed successfully */
    success: boolean;
    /** Exit code from the workflow process */
    exitCode?: number;
    /** Standard output lines */
    stdout?: string[];
    /** Standard error lines */
    stderr?: string[];
    /** Final status: 'completed', 'failed', 'interrupted' */
    status?: 'completed' | 'failed' | 'interrupted';
    /** Unique run ID for this execution */
    runId?: string;
    /** Error message if success is false */
    error?: string;
}

// ============================================================================
// Cortex Complete Types (LLM Inference)
// ============================================================================

/**
 * Message role in a Cortex LLM conversation
 */
export type CortexMessageRole = 'system' | 'user' | 'assistant' | 'tool';

/**
 * Text content block
 */
export interface CortexTextContent {
    type: 'text';
    text: string;
}

/**
 * Image content block (for vision-capable models)
 */
export interface CortexImageContent {
    type: 'image_url';
    image_url: {
        /** Base64 data URL or HTTPS URL */
        url: string;
    };
}

/**
 * Tool result content block (for returning tool call results)
 */
export interface CortexToolResultContent {
    type: 'tool_result';
    tool_use_id: string;
    content: string;
}

/**
 * Message content can be a string or structured content blocks
 */
export type CortexMessageContent =
    | string
    | (CortexTextContent | CortexImageContent | CortexToolResultContent)[];

/**
 * Message in a Cortex LLM conversation
 */
export interface CortexMessage {
    role: CortexMessageRole;
    content: CortexMessageContent;
    /** Tool call ID (required when role is 'tool') */
    tool_call_id?: string;
}

/**
 * JSON Schema for tool function parameters
 */
export interface CortexToolFunctionParameters {
    type: 'object';
    properties: Record<
        string,
        {
            type: string;
            description?: string;
            enum?: string[];
            items?: unknown;
        }
    >;
    required?: string[];
}

/**
 * Tool function definition
 */
export interface CortexToolFunction {
    /** Function name (must match pattern ^[a-zA-Z0-9_-]+$) */
    name: string;
    /** Description of what the function does (helps model decide when to use it) */
    description: string;
    /** JSON Schema for function parameters */
    parameters: CortexToolFunctionParameters;
}

/**
 * Tool definition for Cortex LLM
 */
export interface CortexTool {
    type: 'function';
    function: CortexToolFunction;
}

/**
 * Tool call made by the model
 */
export interface CortexToolCall {
    /** Unique identifier for this tool call */
    id: string;
    type: 'function';
    function: {
        /** Name of the function to call */
        name: string;
        /** JSON string of arguments */
        arguments: string;
    };
}

/**
 * Specific function to force the model to call
 */
export interface CortexForcedFunction {
    name: string;
}

/**
 * Force the model to call a specific tool
 */
export interface CortexForcedToolChoice {
    type: 'function';
    function: CortexForcedFunction;
}

/**
 * Tool choice control for Cortex LLM
 * - 'auto': Model decides whether to call tools (default)
 * - 'none': Never call tools
 * - 'required': Must call at least one tool
 * - object: Force a specific tool
 */
export type CortexToolChoice =
    | 'auto'
    | 'none'
    | 'required'
    | CortexForcedToolChoice;

/**
 * Cortex Guard guardrails configuration
 */
export interface CortexGuardrails {
    /** Enable Cortex Guard content filtering */
    enabled: boolean;
    /** Custom response when content is flagged as unsafe */
    responseWhenUnsafe?: string;
}

/**
 * Cross-region inference configuration
 * Allows routing requests to different Snowflake regions for model availability
 */
export type CortexInferenceRegion =
    | 'auto' // Use account's region (default)
    | 'cross-cloud-any' // Any region across clouds
    | 'aws-global' // AWS cross-region
    | 'aws-us' // AWS US regions
    | 'aws-eu' // AWS EU regions
    | 'aws-apj' // AWS Asia-Pacific
    | 'azure-global' // Azure cross-region
    | 'azure-us' // Azure US regions
    | 'azure-eu'; // Azure EU regions

/**
 * Options for cortexComplete
 */
export interface CortexCompleteOptions {
    /**
     * Model identifier (required).
     * Examples: 'claude-3-5-sonnet', 'llama3.1-70b', 'mistral-large2'
     * See Cortex docs for full list of available models per region.
     */
    model: string;

    /**
     * Messages for completion.
     * Can be a single string (converted to user message) or array of messages.
     */
    messages: string | CortexMessage[];

    /** Temperature (0-1). Higher values = more random. Default: 0.0 */
    temperature?: number;

    /** Nucleus sampling (0-1). Default: 1.0 */
    topP?: number;

    /** Maximum tokens to generate (1-16384). Default: 4096 */
    maxTokens?: number;

    /** Tools available to the model for function calling */
    tools?: CortexTool[];

    /** Control tool usage behavior */
    toolChoice?: CortexToolChoice;

    /** Enable Cortex Guard content filtering */
    guardrails?: CortexGuardrails;

    /** Request timeout in milliseconds. Default: 120000 (2 min) */
    timeout?: number;

    /** Cross-region inference. Default: 'auto' (use account region) */
    region?: CortexInferenceRegion;
}

/**
 * Token usage statistics from Cortex LLM
 */
export interface CortexTokenUsage {
    /** Tokens in the prompt/input */
    promptTokens: number;
    /** Tokens in the completion/output */
    completionTokens: number;
    /** Total tokens (prompt + completion) */
    totalTokens: number;
    /** Cached prompt tokens (prompt caching) */
    promptTokensCached?: number;
}

/**
 * Generated message in a completion choice
 */
export interface CortexChoiceMessage {
    role: 'assistant';
    /** Generated text content (null if only tool calls) */
    content: string | null;
    /** Tool calls made by the model */
    toolCalls?: CortexToolCall[];
}

/**
 * Choice from a Cortex LLM completion
 */
export interface CortexChoice {
    /** Index of this choice */
    index: number;
    /** Generated message */
    message: CortexChoiceMessage;
    /** Why generation stopped */
    finishReason: 'stop' | 'length' | 'tool_calls' | 'content_filter';
}

/**
 * Request details for debugging (included in responses)
 */
export interface CortexCompleteRequestInfo {
    /** Request URL */
    url: string;
    /** Request headers (sanitized - no auth token) */
    headers: Record<string, string>;
    /** Request payload */
    payload: unknown;
}

/**
 * Response from cortexComplete (non-streaming)
 */
export interface CortexCompleteResponse {
    /** Whether the request succeeded */
    success: boolean;
    /** Unique response ID */
    id?: string;
    /** Model used for completion */
    model?: string;
    /** Generated choices (usually 1) */
    choices?: CortexChoice[];
    /** Token usage statistics */
    usage?: CortexTokenUsage;
    /** Error message if success is false */
    error?: string;
    /** HTTP status code (for debugging) */
    statusCode?: number;
    /** Request details for debugging */
    request?: CortexCompleteRequestInfo;
}

// ============================================================================
// Cortex Complete Streaming Types
// ============================================================================

/**
 * Tool call delta in a streaming chunk
 */
export interface CortexStreamDeltaToolCall {
    /** Index of the tool call being built */
    index: number;
    /** Tool call ID (first chunk only) */
    id?: string;
    /** Tool type (first chunk only) */
    type?: 'function';
    /** Function details (accumulated across chunks) */
    function?: {
        /** Function name (first chunk only) */
        name?: string;
        /** Arguments fragment (accumulated) */
        arguments?: string;
    };
}

/**
 * Delta content in a streaming chunk
 */
export interface CortexStreamDelta {
    /** Role (usually only in first chunk) */
    role?: 'assistant';
    /** Content fragment */
    content?: string;
    /** Tool call fragments */
    toolCalls?: CortexStreamDeltaToolCall[];
}

/**
 * Choice in a streaming chunk
 */
export interface CortexStreamChoice {
    /** Choice index */
    index: number;
    /** Delta content */
    delta: CortexStreamDelta;
    /** Finish reason (only in final chunk) */
    finishReason: 'stop' | 'length' | 'tool_calls' | 'content_filter' | null;
}

/**
 * Streaming chunk from cortexCompleteStream
 */
export interface CortexStreamChunk {
    /** Unique chunk ID */
    id: string;
    /** Object type */
    object: 'chat.completion.chunk';
    /** Unix timestamp */
    created: number;
    /** Model used */
    model: string;
    /** Delta choices */
    choices: CortexStreamChoice[];
    /** Usage statistics (only in final chunk when requested) */
    usage?: CortexTokenUsage;
}

/**
 * Interface for the P67 Agent SDK
 * Defines the public API for interacting with Snowflake and Cortex services
 */
export interface WorkflowSDK {
    /**
     * Gets a parameter from the 'parameters' field of the config
     * @param name - The name of the parameter
     * @param config_name - The name of the config to use, if null, the only one will be used
     * @returns The value of the parameter
     * @throws {Error} If the parameter is not found
     */
    getParameter(name: string, config_name?: string): string | undefined;

    /**
     * Gets all parameters from the 'parameters' field of the config
     * @param config_name - The name of the config to use, if null, the only one will be used
     * @returns The parameters as a record of name-value pairs
     */
    getParameters(config_name?: string): Record<string, string>;

    /**
     * Executes a SQL query against Snowflake
     *
     * Executes any SQL statement including DML (INSERT, UPDATE, DELETE) and DDL (CREATE, ALTER, DROP).
     * For read-only queries, prefer using `executeQueryReadOnly` which validates the query type.
     *
     * @param stmt - Snowflake statement to execute
     *   - `sqlText`: SQL text to execute
     *   - `binds`: Binds to use for the statement
     * @param config_name - Optional name of the Snowflake config to use. If not provided and only
     *                      one config exists, that config will be used automatically.
     * @returns Query results containing the statement metadata and result rows
     * @throws Error if query execution fails
     *
     * @example
     * const result = await sdk.executeQuery({
     *   sqlText: 'INSERT INTO my_table (col1) VALUES (?)',
     *   binds: ['value1']
     * });
     *
     * @example
     * // Using a specific config
     * const result = await sdk.executeQuery(
     *   {
     *     sqlText: 'UPDATE orders SET status = ? WHERE id = ?',
     *     binds: ['shipped', 123]
     *   },
     *   'production_config'
     * );
     */
    executeQuery(
        stmt: SnowflakeStatement,
        config_name?: string,
    ): Promise<QueryResult>;

    /**
     * Executes a read-only SELECT query against Snowflake
     *
     * Validates that the query is read-only before execution.
     * Allows SELECT, WITH (CTE), SHOW, and DESCRIBE statements.
     * Rejects DML (INSERT, UPDATE, DELETE) and DDL (CREATE, ALTER, DROP) statements for safety.
     *
     * @param stmt - Snowflake statement to execute
     *   - `sqlText`: SQL text to execute
     *   - `binds`: Binds to use for the statement
     * @param config_name - Optional name of the Snowflake config to use. If not provided and only
     *                      one config exists, that config will be used automatically.
     * @returns Query results containing the statement metadata and result rows
     * @throws Error if the query is not read-only, contains multiple statements, or execution fails
     *
     * @example
     * const result = await sdk.executeQueryReadOnly({
     *   sqlText: 'SELECT * FROM my_table LIMIT 10',
     *   binds: []
     * });
     * console.log(result.rows);
     *
     * @example
     * // Using a specific config
     * const result = await sdk.executeQueryReadOnly(
     *   {
     *     sqlText: 'SELECT COUNT(*) FROM orders',
     *     binds: []
     *   },
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
     * @param options - Options for the email:
     *   - `email_addresses`: Array of email addresses to send the email to
     *   - `subject`: Subject of the email
     *   - `body`: Body of the email
     *   - `content_type`: Content type of the email
     *   - `integration_name`: Name of the email integration to use. If not provided, the default email integration will be used.
     * @param config_name - Optional name of the Snowflake config to use. If not provided and only
     *                      one config exists, that config will be used automatically.
     * @returns Promise that resolves to true if the email is sent successfully, false otherwise
     *
     * @example
     * const response = await sdk.email({
     *   email_addresses: ['test@example.com'],
     *   subject: 'Test Subject',
     *   body: 'Test Body',
     *   integration_name: 'test_integration'
     * });
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

    /**
     * Makes an HTTP request to an external service
     *
     * If `oauthRef` is provided, automatically:
     * - Retrieves the OAuth token from secrets
     * - Refreshes the token if expired (when refresh_token is available)
     * - Adds `Authorization: Bearer <token>` header
     *
     * @param options - Request configuration
     *   - `url`: The URL to request (required)
     *   - `method`: HTTP method (defaults to 'GET')
     *   - `headers`: Additional request headers
     *   - `body`: Request body (JSON serialized if object)
     *   - `oauthRef`: OAuth secret reference for Bearer token injection
     *   - `timeout`: Request timeout in milliseconds (default 30000)
     * @returns Response object with `success`, `status`, `headers`, `data` or `error`.
     *          Never throws - errors are returned in the response object.
     *
     * @example
     * // Simple GET request with OAuth
     * const response = await sdk.httpRequest({
     *     url: 'https://api.github.com/user',
     *     oauthRef: 'github_oauth',
     * });
     *
     * if (response.success) {
     *     console.log('User:', response.data);
     * } else {
     *     console.error('Error:', response.error);
     * }
     *
     * @example
     * // POST request with body
     * const response = await sdk.httpRequest({
     *     url: 'https://api.example.com/data',
     *     method: 'POST',
     *     headers: { 'Content-Type': 'application/json' },
     *     body: { key: 'value' },
     *     oauthRef: 'example_oauth',
     * });
     *
     * @example
     * // Request without OAuth (manual auth)
     * const response = await sdk.httpRequest({
     *     url: 'https://api.example.com/public',
     *     headers: { 'X-API-Key': sdk.getParameter('api_key') },
     * });
     */
    httpRequest(options: HttpRequestOptions): Promise<HttpResponse>;

    /**
     * Pauses workflow execution and waits for human input.
     *
     * The payload is surfaced to callers who can then provide a response
     * via the controld API. Execution resumes when a response is provided.
     *
     * @param payload - JSON-serializable value to surface (question, form data, etc.)
     * @param options - Optional configuration
     *   - `timeout`: Optional timeout in ms (default: no timeout - waits indefinitely)
     *   - `nodeId`: Optional node identifier for debugging
     * @returns The response provided by the human
     * @throws Error if timeout is reached (when specified)
     *
     * @example
     * // Simple approval flow
     * const approved = await sdk.interrupt({
     *   question: "Approve this action?",
     *   details: { amount: 500, recipient: "vendor@example.com" }
     * });
     *
     * if (approved) {
     *   await sdk.executeQueryReadOnly({ sqlText: 'SELECT 1' });
     * }
     *
     * @example
     * // Collecting user input
     * const userLocation = await sdk.interrupt<string>({
     *   type: "input",
     *   prompt: "What city are you in?"
     * });
     * console.log(`User is in: ${userLocation}`);
     */
    interrupt<T = unknown>(
        payload: unknown,
        options?: InterruptOptions,
    ): Promise<T>;

    /**
     * Generates text completion using Snowflake Cortex LLM (non-streaming)
     *
     * Calls the Cortex REST API to generate text using the specified model.
     * Supports conversations, tool calling, vision, and content filtering.
     *
     * @param options - Completion configuration
     *   - `model`: Model identifier (required, e.g., 'claude-3-5-sonnet', 'llama3.1-70b')
     *   - `messages`: Single prompt string or array of conversation messages
     *   - `temperature`: Randomness control (0-1, default 0.0)
     *   - `topP`: Nucleus sampling (0-1, default 1.0)
     *   - `maxTokens`: Max output tokens (1-16384, default 4096)
     *   - `tools`: Tools available for function calling
     *   - `toolChoice`: Control tool usage ('auto', 'none', 'required', or specific tool)
     *   - `guardrails`: Cortex Guard content filtering configuration
     *   - `timeout`: Request timeout in milliseconds (default 120000)
     *   - `region`: Cross-region inference configuration
     * @param config_name - Optional Snowflake config name
     * @returns Response with choices, usage stats, request info, or error.
     *          Never throws - errors are returned in the response object.
     *
     * @example
     * // Simple prompt
     * const response = await sdk.cortexComplete({
     *   model: 'claude-3-5-sonnet',
     *   messages: 'Explain quantum computing in one paragraph.'
     * });
     *
     * if (response.success) {
     *   console.log(response.choices?.[0].message.content);
     *   console.log(`Tokens used: ${response.usage?.totalTokens}`);
     * } else {
     *   console.error(response.error);
     *   console.error('Request:', response.request);
     * }
     *
     * @example
     * // Multi-turn conversation
     * const response = await sdk.cortexComplete({
     *   model: 'llama3.1-70b',
     *   messages: [
     *     { role: 'system', content: 'You are a helpful data analyst.' },
     *     { role: 'user', content: 'What is a JOIN in SQL?' },
     *     { role: 'assistant', content: 'A JOIN combines rows from two tables...' },
     *     { role: 'user', content: 'Show me an example with INNER JOIN.' }
     *   ],
     *   temperature: 0.7,
     *   maxTokens: 1000
     * });
     *
     * @example
     * // Tool calling
     * const response = await sdk.cortexComplete({
     *   model: 'claude-3-5-sonnet',
     *   messages: [{ role: 'user', content: 'What is the weather in NYC?' }],
     *   tools: [{
     *     type: 'function',
     *     function: {
     *       name: 'get_weather',
     *       description: 'Get current weather for a location',
     *       parameters: {
     *         type: 'object',
     *         properties: {
     *           location: { type: 'string', description: 'City name' }
     *         },
     *         required: ['location']
     *       }
     *     }
     *   }]
     * });
     *
     * if (response.choices?.[0].message.toolCalls) {
     *   const toolCall = response.choices[0].message.toolCalls[0];
     *   const args = JSON.parse(toolCall.function.arguments);
     *   console.log(`Calling ${toolCall.function.name} with:`, args);
     *   // Execute the tool, then continue conversation with tool result...
     * }
     *
     * @example
     * // Cross-region inference
     * const response = await sdk.cortexComplete({
     *   model: 'claude-3-5-sonnet',
     *   messages: 'Hello!',
     *   region: 'aws-us'  // Route to AWS US regions
     * });
     */
    cortexComplete(
        options: CortexCompleteOptions,
        config_name?: string,
    ): Promise<CortexCompleteResponse>;

    /**
     * Generates streaming text completion using Snowflake Cortex LLM
     *
     * Returns an async iterable that yields chunks as they arrive from the model.
     * Ideal for real-time UIs, long-form content generation, or showing progress.
     *
     * @param options - Completion configuration (same as cortexComplete)
     * @param config_name - Optional Snowflake config name
     * @returns Async iterable of streaming chunks. Throws on request initiation failure.
     *
     * @example
     * // Stream to console
     * const stream = sdk.cortexCompleteStream({
     *   model: 'claude-3-5-sonnet',
     *   messages: 'Write a poem about data warehouses.'
     * });
     *
     * let fullContent = '';
     * for await (const chunk of stream) {
     *   const delta = chunk.choices[0]?.delta?.content;
     *   if (delta) {
     *     process.stdout.write(delta);
     *     fullContent += delta;
     *   }
     *   // Check for usage in final chunk
     *   if (chunk.usage) {
     *     console.log(`\nTotal tokens: ${chunk.usage.totalTokens}`);
     *   }
     * }
     *
     * @example
     * // Collect tool calls from stream
     * const toolCalls = new Map<number, { id: string; name: string; args: string }>();
     *
     * for await (const chunk of sdk.cortexCompleteStream({
     *   model: 'claude-3-5-sonnet',
     *   messages: [{ role: 'user', content: 'Get weather for NYC and LA' }],
     *   tools: [weatherTool]
     * })) {
     *   for (const choice of chunk.choices) {
     *     if (choice.delta.toolCalls) {
     *       for (const tc of choice.delta.toolCalls) {
     *         const existing = toolCalls.get(tc.index) || { id: '', name: '', args: '' };
     *         if (tc.id) existing.id = tc.id;
     *         if (tc.function?.name) existing.name = tc.function.name;
     *         if (tc.function?.arguments) existing.args += tc.function.arguments;
     *         toolCalls.set(tc.index, existing);
     *       }
     *     }
     *     if (choice.finishReason === 'tool_calls') {
     *       console.log('Tool calls:', Array.from(toolCalls.values()));
     *     }
     *   }
     * }
     *
     * @example
     * // Error handling with try-catch
     * try {
     *   for await (const chunk of sdk.cortexCompleteStream({
     *     model: 'invalid-model',
     *     messages: 'Hello'
     *   })) {
     *     console.log(chunk);
     *   }
     * } catch (error) {
     *   console.error('Stream failed:', error);
     * }
     */
    cortexCompleteStream(
        options: CortexCompleteOptions,
        config_name?: string,
    ): AsyncIterable<CortexStreamChunk>;

    /**
     * Executes another workflow as a subworkflow
     *
     * Runs a workflow by ID or by name, optionally passing runtime parameters.
     * When running by name, the latest version of the workflow is used.
     *
     * @param options - Subworkflow configuration:
     *   - `workflowId`: Run by ID (mutually exclusive with workflowName)
     *   - `workflowName`: Run by name, uses latest version (mutually exclusive with workflowId)
     *   - `params`: Optional runtime parameter overrides
     *   - `timeout`: Request timeout in milliseconds (default 300000 = 5 min)
     * @param config_name - Optional name of the Snowflake config to use for authentication
     * @returns Response with success status, stdout, stderr, exit code, and run ID.
     *          Never throws - errors are returned in the response object.
     *
     * @example
     * // Run by name with parameters
     * const result = await sdk.executeSubworkflow({
     *   workflowName: 'data-pipeline',
     *   params: { env: 'prod', batchSize: '100' }
     * });
     *
     * if (result.success) {
     *   console.log(`Completed with status: ${result.status}`);
     *   console.log(`Output: ${result.stdout?.join('\n')}`);
     * } else {
     *   console.error(`Failed: ${result.error}`);
     * }
     *
     * @example
     * // Run by ID
     * const result = await sdk.executeSubworkflow({
     *   workflowId: 'abc-123-uuid',
     *   params: { targetTable: 'SALES' }
     * });
     */
    executeSubworkflow(
        options: SubworkflowOptions,
        config_name?: string,
    ): Promise<SubworkflowResponse>;
}
