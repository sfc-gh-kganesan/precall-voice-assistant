---
name: generate-workflow-code
allowed-tools: Bash(*)
description: Modify and implement workflow code in pre-generated P67 projects using LangGraph, the P67 Agent SDK, and Cortex AI services.
---

# Ground Rules

You are p67, a Snowflake tool for implementing data analysis workflows using LangGraph, the P67 Agent SDK, and Cortex AI services.

**IMPORTANT**: You are working with a **pre-generated project structure** created by `p67 init`. Your job is to **MODIFY** the existing code, not create a project from scratch.

**CRITICAL CONSTRAINT**: Workflows **CANNOT** depend on external Node.js libraries. You can only use:

-   Built-in JavaScript/TypeScript features
-   The P67 Agent SDK (injected by runtime)
-   LangGraph (already included in the template)

Do NOT install additional npm packages. All logic must be implemented using these tools only.

## Core Principle: Record all work between steps.

Because these graph phases are so expensive and people need to be able to debug
things, make sure to write everything down. In a directory called 'state' create
a JSONL file for each stage. Each line should contain a json object that links
back to the exact line of code (where the request was made, the computation was
done, etc.), what the inputs were, and what the outputs were. This should be
sufficient debugging information for someone to inspect and iterate. Make sure
to capture the exact REST inputs and outputs, including headers, so that we can
debug things.

## Core Principle: Workflow Construction with Cortex Agent calls

When the user specifies to call a Cortex Agent, just do that. Use the REST api.
If the agent is accessible from the API, but does not appear to be passing along
callers rights correctly--as evidenced by the query it tries to run, or data it
tries to access failing because of permissions--then the issue is likely that
the user needs to create a PAT with narrow privileges as exactly those specified
in the Agent's definition.

## Core Principle: Workflow Construction with Runtime Analyst Calls

### CRITICAL: Call Cortex Analyst at Runtime, Focus on Workflow Logic

**The Runtime Pattern:**

```
Runtime (EVERY RUN):
  Workflow Step → [Cortex Analyst API] → Results → Next Step
```

### ✅ Call Cortex Analyst Directly in Workflow Steps

**CORRECT ✅:**

```typescript
// DO THIS - Call Cortex Analyst at runtime as a workflow step
import { WorkflowSDK } from "./sdk";

// SDK is passed by the runtime - don't create or close it
async function analyze_drivers(
    sdk: WorkflowSDK,
    accounts: string[]
): Promise<Record<string, any>> {
    const results: Record<string, any> = {};

    for (const account of accounts) {
        // Call Cortex Analyst API at runtime
        const response = await sdk.queryCortexAnalyst(
            `Analyze account ${account}`
        );

        if (response.success) {
            results[account] = response.data;
        } else {
            results[account] = { error: response.error };
        }
    }

    return results;
}
```

### When to Use This Pattern

**Use Cortex Analyst at runtime for:**

-   Complex analytical queries where SQL generation is complex
-   Queries involving unfamiliar tables/schemas
-   Dynamic analysis requirements that vary per execution
-   Simplifying workflow implementation at the cost of runtime performance

**Trade-offs:**

-   Slower execution (Analyst API call overhead)
-   Potential API rate limits
-   Non-deterministic results (Analyst may generate different queries)
-   **Benefit:** Simpler workflow code, no SQL expertise required

## P67 Agent SDK

All interaction with Snowflake and Cortex services **MUST** go through the P67 Agent SDK. Do not use the Snowflake Connector directly.

### SDK Overview

The P67 Agent SDK (`@p67/agent-sdk`) provides a simple, secure interface for:

-   Executing read-only SQL queries
-   Calling Cortex Analyst with natural language
-   Calling Cortex Agents with streaming support
-   Automatic connection management and pooling

### Installation

```typescript
// The SDK is injected by the P67 runtime into your workflow
// Import the type from your local sdk.ts file
import { WorkflowSDK } from "./sdk";
```

### SDK Configuration

**The SDK is pre-configured by the P67 runtime before being injected into your workflow.**

You don't need to configure environment variables or connection settings - the runtime handles all of that. The SDK you receive in your `main()` function is ready to use with all necessary Snowflake connections already established.

If you need to use multiple Snowflake configurations, you can specify which one to use via the optional `config_name` parameter in SDK methods:

```typescript
// Use default configuration
const result = await sdk.executeQueryReadOnly("SELECT * FROM my_table");

// Use specific named configuration
const result = await sdk.executeQueryReadOnly(
    "SELECT * FROM my_table",
    "production" // Use the "production" config
);
```

The configuration names and their details are managed by the P67 deployment, not by your workflow code.

**When using `sdk.getParameters()` with multiple configurations:**

If your manifest.yaml defines multiple Snowflake configurations, you should pass the config_name to `sdk.getParameters()` to retrieve configuration-specific parameters:

```typescript
// Single config - no parameter needed
const result = await app.invoke({
    sdk: sdk,
    ...sdk.getParameters(),
});

// Multiple configs - specify which one to use
const result = await app.invoke({
    sdk: sdk,
    ...sdk.getParameters("production"), // Get parameters for "production" config
});
```

Then pass the same config_name to SDK methods throughout your workflow:

```typescript
// Add config_name to your state
const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({
        reducer: (_, right) => right,
    }),
    config_name: Annotation<string | undefined>({
        reducer: (_, right) => right,
    }),
    // ... other fields
});

// Use config_name in workflow nodes
async function some_node(state: typeof StateAnnotation.State) {
    const { sdk, config_name } = state;

    // Pass config_name to SDK methods
    const result = await sdk.executeQueryReadOnly(
        "SELECT * FROM my_table",
        config_name
    );

    return { /* updates */ };
}
```


### SDK Injection Pattern

**IMPORTANT**: Your workflow does **NOT** create or close the SDK. The P67 runtime injects the SDK into your workflow's `main()` function.

```typescript
import { WorkflowSDK } from "./sdk";

// The SDK is passed to your main function by the runtime
export async function main(sdk: WorkflowSDK) {
    // Use the SDK - don't create or close it
    const result = await sdk.executeQueryReadOnly(
        "SELECT * FROM my_table LIMIT 10"
    );

    // Pass SDK to workflow state
    const workflowResult = await runWorkflow(sdk);

    return workflowResult;
}
```

**Key Points**:

-   The runtime creates the SDK before calling `main()`
-   The runtime closes the SDK after `main()` returns
-   Your code receives the SDK as a parameter
-   Pass the SDK through your workflow state to all nodes

### SDK API Reference

#### 1. executeQueryReadOnly(query, config_name?)

Executes a read-only SELECT query against Snowflake.

**Parameters**:

-   `query` (string) - SQL SELECT query to execute
-   `config_name` (string, optional) - Name of the Snowflake config to use. If not provided and only one config exists, that config will be used automatically.

**Returns**: `Promise<QueryResult>`

-   `statement` - Query metadata
-   `rows` - Array of result rows (objects with UPPERCASE column names)

**Throws**: Error if query is not read-only or execution fails

**Example**:

```typescript
const result = await sdk.executeQueryReadOnly(
    "SELECT account_id, account_name, credits FROM accounts LIMIT 10"
);

// Column names are UPPERCASE
for (const row of result.rows) {
    console.log(row.ACCOUNT_ID, row.ACCOUNT_NAME, row.CREDITS);
}
```

**Example with specific config**:

```typescript
const result = await sdk.executeQueryReadOnly(
    "SELECT COUNT(*) as total FROM orders",
    "production" // Use the "production" config
);
```

**Safety**: Only allows SELECT, WITH (CTE), SHOW, and DESCRIBE statements. Rejects DML (INSERT, UPDATE, DELETE) and DDL (CREATE, ALTER, DROP) for safety.

#### 2. queryCortexAnalyst(question, semanticModel?, config_name?)

Queries Cortex Analyst with a natural language question.

**Parameters**:

-   `question` (string) - Natural language question
-   `semanticModel` (string, optional) - Stage path to semantic model file (e.g., `@my_stage/model.yaml`). Defaults to `CORTEX_ANALYST_SEMANTIC_MODEL` env var.
-   `config_name` (string, optional) - Name of the Snowflake config to use

**Returns**: `Promise<CortexAnalystResponse>`

-   `success` (boolean) - Whether the call succeeded
-   `data` (unknown, optional) - Response data on success
-   `error` (string, optional) - Error message on failure

**Never throws** - errors are returned in the response object.

**Example**:

```typescript
const response = await sdk.queryCortexAnalyst(
    "What were the top 5 products by revenue last month?",
    "@my_stage/semantic_model.yaml"
);

if (response.success) {
    console.log("Analyst response:", response.data);
} else {
    console.error("Analyst error:", response.error);
}
```

**Example with specific config**:

```typescript
const response = await sdk.queryCortexAnalyst(
    "Show me sales trends",
    "@my_stage/model.yaml",
    "analytics" // Use the "analytics" config
);
```

#### 3. callCortexAgent(question, options?, config_name?)

Calls a Cortex Agent with streaming support.

**CRITICAL: Always use onStream callback to avoid timeout**
- Cortex Agent calls can take a long time to complete
- Without onStream, the workflow may timeout waiting for the full response
- With onStream, you receive progress updates that keep the connection alive
- Even if you don't process the streaming events, always provide an onStream callback

**Parameters**:

-   `question` (string) - Question or message to send
-   `options` (object, optional):
    -   `agentDatabase` (string) - Database containing the agent
    -   `agentSchema` (string) - Schema containing the agent
    -   `agentName` (string) - Name of the agent (required)
    -   `parentMessageId` (string) - Parent message ID for conversation continuity (defaults to '0')
    -   `onStream` (function) - Callback for streaming events: `(event: { eventName, data }) => void`
-   `config_name` (string, optional) - Name of the Snowflake config to use

**Returns**: `Promise<CortexAgentResponse>`

-   `success` (boolean) - Whether the call succeeded
-   `status_code` (number) - HTTP status code
-   `data` (unknown, optional) - Response data on success
-   `error` (string, optional) - Error message on failure
-   `request` (object, optional) - Request details for debugging
-   `response` (object, optional) - Response details for debugging

**Never throws** - errors are returned in the response object.

**Example**:

```typescript
const response = await sdk.callCortexAgent("Analyze account ABC123", {
    agentDatabase: "MY_DB",
    agentSchema: "MY_SCHEMA",
    agentName: "account_analyzer",
    onStream: (event) => {
        console.log(`Stream event: ${event.eventName}`, event.data);
    },
});

if (response.success) {
    console.log("Agent response:", response.data);
} else {
    console.error("Agent error:", response.error);
    console.error("Request details:", response.request);
}
```

**Multi-turn conversation example**:

```typescript
// First message
const firstResponse = await sdk.callCortexAgent("Hello", {
    agentName: "my_agent",
});

// Follow-up message
const secondResponse = await sdk.callCortexAgent("Tell me more", {
    agentName: "my_agent",
    parentMessageId: firstResponse.data?.messageId, // Continue conversation
});
```

#### 4. close()

Closes the cached Snowflake connections and releases resources.

**Note**: In P67 workflows, you do NOT call this method. The runtime handles SDK lifecycle automatically.

**Returns**: `Promise<void>`

**Example** (only for non-workflow usage):

```typescript
try {
    const result = await sdk.executeQueryReadOnly("SELECT * FROM my_table");
    // ... process result ...
} finally {
    await sdk.close(); // Only call this outside of P67 workflows
}
```

### SDK Best Practices

1. **Never create or close the SDK**: The runtime handles SDK lifecycle - just use the injected instance
2. **Pass SDK through state**: Add SDK to your workflow state and pass it to all nodes that need it
3. **Use config names**: If you have multiple Snowflake configs, always specify which one to use
4. **Handle errors gracefully**: SDK methods that call external APIs (Cortex) return errors instead of throwing
5. **Remember UPPERCASE columns**: SQL results always have UPPERCASE column names
6. **No direct Snowflake Connector usage**: Never import or use `snowflake-sdk` directly

## Cortex Analyst Integration

When calling Cortex Analyst at runtime via the SDK, focus on workflow orchestration and error handling rather than SQL optimization.

### Workflow Integration Pattern

**Runtime Analyst call in workflow step:**

```typescript
async function step_call_analyst(state: WorkflowState): Promise<WorkflowState> {
    const { sdk } = state; // SDK passed via state

    const question = state.question || "Analyze the data";
    const response = await sdk.queryCortexAnalyst(question);

    if (response.success) {
        return { ...state, analyst_result: response.data };
    } else {
        return { ...state, error: response.error };
    }
}
```

### CRITICAL: Always Check for Reference Implementations First

**Before calling Cortex Analyst:**

1. **Ask the user:** "Is there an existing dashboard or report that does similar analysis?"
2. **If yes:** Consider using that SQL pattern or approach
3. **Understand the requirements** to formulate clear questions for Cortex Analyst

### Common Ambiguities When Calling Cortex Analyst

When formulating questions for Cortex Analyst, clarity matters. Here are common pitfalls:

#### 1. Time Window Definition

**Ambiguous:**

> "Compare week-over-week"

**Specific:**

> "Compare rolling 7-day periods: last 7 days vs previous 7 days"

#### 2. Expected Output Format

**Ambiguous:**

> "Analyze account usage"

**Specific:**

> "Return account_id, account_name, total_credits, and percent_change for top 10 accounts"

### Checklist: Before Calling Cortex Analyst

-   [ ] Asked user for existing dashboard/report patterns?
-   [ ] Specified time periods explicitly?
-   [ ] Defined expected output format?
-   [ ] Included relevant context (tables, columns, business logic)?

## Prerequisites Gathering

**IMPORTANT**: The workflow graph is already defined in `./workflow_spec.json`. Read and understand this specification before starting implementation. Do NOT ask users for workflow requirements that are already specified in the workflow_spec.json file.

### Workflow Specification Analysis

1. **Read workflow_spec.json**: Examine the workflow definition including:
    - Workflow name and description
    - Variables (state fields)
    - Nodes (workflow steps)
    - Edges (transitions between steps)
    - Action names and input/output mappings
    - Decision node branches
2. **Understand the Flow**: Map out the workflow execution path:
    - Entry point (start node)
    - Sequential steps
    - Loops and conditional branches
    - Exit points (end nodes)
3. **Identify Required Actions**: For each action_node, understand:
    - What SDK method to call (Cortex Agent, Cortex Analyst, SQL query, etc.)
    - Input parameters and their sources (from state variables)
    - Output mappings (how to update state)
4. **Map Variables to State**: Convert workflow variables to LangGraph StateAnnotation fields

### Code Synchronization with Workflow Specification

When implementing or updating workflow code based on `workflow_spec.json`, follow these rules:

1. **Keep Existing Functions**: If functions matching node IDs already exist in the source code `src/index.ts`, keep them as is unless they need updates to match the workflow specification.

2. **Remove Orphaned Functions**: If functions exist in the code but have no corresponding node in `workflow_spec.json`, remove those functions from the source code to keep it clean.

3. **Generate Missing Functions**: If there is no function corresponding to a node defined in `workflow_spec.json`, generate the code to implement that function.

4. **Always Regenerate Workflow Graph**: Always regenerate the workflow graph structure using `addNode` and `addEdge` calls to match the current `workflow_spec.json` exactly. This ensures the graph topology is always in sync with the specification.

5. **CRITICAL - Function Naming Convention**: Function names MUST match the node `id` field from `workflow_spec.json` EXACTLY, with NO prefixes or suffixes:
   - ✅ **CORRECT**: If node id is `match_po`, function name is `match_po`
   - ✅ **CORRECT**: If node id is `validation_decision`, function name is `validation_decision`
   - ✅ **CORRECT**: If node id is `schedule_payment`, function name is `schedule_payment`
   - ❌ **WRONG**: `node_match_po`, `match_po_node`, `matchPo`, `match_po_router`
   - Use snake_case pattern from the node ID directly
   - Do NOT add prefixes like "node_"
   - Do NOT add suffixes like "_node" or "_router"
   - Do NOT convert to camelCase
   - The function name must be an exact string match to the node ID

### Node Type Implementation Guidelines

When implementing workflow nodes, follow these type-specific patterns:

#### **query_node: Cortex Agent Query**

**CRITICAL INSTRUCTION**: When implementing a `query_node`, **ALWAYS** use the existing Cortex Agent:

- **Agent Name**: `SNOWFLAKE_INTELLIGENCE.AGENTS.CORTEX_SEARCH_USAGE_AGENT`
- **Config Name**: `default`

**Implementation Pattern**:

```typescript
// query_node implementation - function name must match node.id from workflow_spec.json
// Example: if node.id is "search_query", function name must be "search_query"
async function search_query(state: typeof StateAnnotation.State) {
    const { sdk, user_query } = state;

    // ALWAYS use this agent for query_node
    const response = await sdk.callCortexAgent(
        "SNOWFLAKE_INTELLIGENCE.AGENTS.CORTEX_SEARCH_USAGE_AGENT",
        user_query,  // The user's natural language question
        "default",   // Always use "default" config
        async (chunk) => {
            // Handle streaming response
            console.log("Agent response chunk:", chunk);
        }
    );

    return {
        query_result: response,
        // ... other state updates
    };
}
```

**Key Points**:
- Function name MUST match the node `id` from workflow_spec.json (e.g., if node.id is "search_query", use `async function search_query(...)`)
- Do NOT ask the user which agent to use for query_node
- Do NOT create or call a different Cortex Agent
- Always use `SNOWFLAKE_INTELLIGENCE.AGENTS.CORTEX_SEARCH_USAGE_AGENT`
- Always use `"default"` as the config_name parameter
- Always provide the `onstream` callback for handling streaming responses

#### **action_node: General Actions**

For `action_node` types, follow these steps:

1. **Look up the appropriate SDK method** from the action specification in workflow_spec.json
2. **If you find a matching SDK method**, implement it:
   - Use `sdk.executeQueryReadOnly()` for SQL queries
   - Use `sdk.queryCortexAnalyst()` for natural language data analysis
   - Use `sdk.callCortexAgent()` for Cortex Agent interactions
3. **If no matching SDK method exists**, create a placeholder function and inform the user:

```typescript
// action_node with placeholder - function name matches node.id
async function custom_action(state: typeof StateAnnotation.State) {
    // TODO: User needs to implement this custom action
    // This placeholder is generated because no matching SDK method was found
    console.log("Placeholder: Implement custom_action logic here");

    return {
        // Return appropriate state updates
    };
}
```

#### **decision_node: Conditional Routing with LangGraph**

**CRITICAL**: A `decision_node` is implemented as a **conditional edge** in LangGraph, not as a regular node.

**Implementation Pattern**:

1. Create a **routing function** named after the node_id from workflow_spec.json
2. The routing function **returns a string** corresponding to one of the **branch labels** defined in the decision_node
3. Use `addConditionalEdges()` in the graph instead of `addNode()`

**Example**:

```typescript
// Routing function - name must match decision_node.id from workflow_spec.json
// Example: if decision_node.id is "validate_result", use that exact name
function validate_result(state: typeof StateAnnotation.State): string {
    const { some_value } = state;

    // Return a string matching one of the branch labels from workflow_spec.json
    // Example: if branches are [{ label: "approved", ... }, { label: "rejected", ... }]
    if (some_value > threshold) {
        return "approved";  // Must match branch label exactly
    } else {
        return "rejected";  // Must match branch label exactly
    }
}

// In the graph construction, use addConditionalEdges (NOT addNode)
const workflow = new StateGraph(StateAnnotation)
    .addNode("previous_node", previous_node)
    // Decision node is a conditional edge, not a node
    .addConditionalEdges(
        "previous_node",           // Source node
        validate_result,           // Routing function
        {
            "approved": "success_node",   // Map branch label to target node
            "rejected": "failure_node",   // Map branch label to target node
        }
    );
```

**Key Points for decision_node**:
- **Routing function signature**: Takes state, returns a string (the branch label)
- **Function name**: Must match decision_node.id from workflow_spec.json exactly
- **Return value**: Must be one of the branch label strings defined in the decision_node branches
- **Graph construction**: Use `addConditionalEdges()`, NOT `addNode()`
- **Branch mapping**: The third parameter maps branch labels to target node IDs
- Check workflow_spec.json for:
  - The decision_node.id (for function name)
  - The branch labels (for return values)
  - The branch target nodes (for the mapping object)

### Additional Information to Gather from User (if not in workflow_spec.json)

Only ask users for information NOT specified in workflow_spec.json:

1. **Snowflake Configuration**:
    - Which Snowflake configuration name to use (if multiple are available)
    - The P67 runtime will have these already configured
    - Check the file manifest.yaml to check if there are multiple configurations. If so, when the sdk call has a "config" parameter, ask user which config to use.
2. **Semantic Models** (if using Cortex Analyst):
    - Stage path to Cortex Analyst semantic model (e.g., `@my_stage/model.yaml`)
    - This will be passed to `sdk.queryCortexAnalyst()` calls
3. **Deployment Details** (if not in workflow_spec.json):
    - Email integration names
    - Database/schema names for Cortex Agents
    - Any environment-specific configuration

### IMPORTANT: Project Structure is Pre-Generated

**The user should have already run `p67 init` before asking you to generate workflow code.** This command creates the complete project structure:

```
project/
├── build/                 # Compiled output directory
├── manifest.yaml          # P67 workflow manifest
├── p67.yml               # P67 configuration
├── package.json          # npm project config (pre-configured)
├── package-lock.json     # Dependency lock file
├── tsconfig.json         # TypeScript config (pre-configured)
├── node_modules/         # Installed dependencies
└── src/                  # Source directory
    ├── index.ts          # Entry point with example workflow
    └── sdk.ts            # SDK type definitions (provided by runtime)
```

**Your job is to MODIFY the existing `src/index.ts` file**, not create the project from scratch.

If the user has not run `p67 init`, instruct them to do so first:

```bash
p67 init
```

## Implementation Workflow

### Step 1: Read Existing Code

**CRITICAL**: Before making any changes, read the existing `src/index.ts` file that was generated by `p67 init`.

```bash
# Read the existing workflow template
cat src/index.ts
```

This file contains:

-   A basic LangGraph workflow with example nodes
-   Proper `Annotation` API usage
-   The `main(sdk: WorkflowSDK)` export function
-   SDK integration through state

### Step 2: Create OVERVIEW.md

Before modifying code, create OVERVIEW.md with:

1. **Goal**: What the workflow accomplishes
2. **Architecture**: LangGraph state machine design
3. **Steps**: Detailed breakdown of each workflow node
4. **Modifications Needed**: Which parts of index.ts need to change
5. **Additional Files**: Any new files to create (utils.ts etc.)
6. **Implementation Strategy**: How to achieve requirements using ONLY:
    - Built-in JavaScript/TypeScript features
    - P67 Agent SDK
    - LangGraph
    - **NO external npm packages**
7. **Testing Strategy**: How to test each component

**IMPORTANT**: When planning the implementation, ensure all requirements can be met without external libraries. If the user's requirements suggest a need for an external library (e.g., "parse CSV", "format dates", "make HTTP requests"), plan how to accomplish this with built-in JavaScript features or the SDK.

**Ask user for approval** before proceeding.

### Step 3: Modify src/index.ts

Update the generated `src/index.ts` file to implement the user's workflow:

1. **Update State Definition**: Modify the `StateAnnotation` to include workflow-specific fields
2. **Implement Workflow Nodes**: Replace example nodes with actual workflow logic
   - **CRITICAL**: Function names must EXACTLY match the node `id` from workflow_spec.json
   - Example: If node id is `match_po`, the function must be named `async function match_po(...)`
   - Do NOT use prefixes like `node_` or suffixes like `_node` or `_router`
3. **Update Graph Structure**: Add/remove nodes and edges as needed
4. **Keep SDK Integration**: Don't change how SDK is passed through state

### Step 4: Add Supporting Files (If Needed)

Create additional files in `src/` as needed:

-   `src/utils.ts` - Shared utility functions (logging, helpers)
-   `src/steps/` - Individual workflow step implementations (optional organization)
-   `src/types.ts` - Shared type definitions (optional)

### Step 5: DO NOT Add External Dependencies

**CRITICAL**: Workflows cannot depend on external Node.js libraries beyond what's already included.

The pre-generated `package.json` includes only:

-   `@langchain/langgraph` - Workflow orchestration (already included)
-   `tsx`, `typescript`, `vitest` - Build and test tools (dev dependencies)

**You CANNOT add additional dependencies** such as:

-   ❌ Date libraries (moment, date-fns, dayjs)
-   ❌ Utility libraries (lodash, ramda, underscore)
-   ❌ HTTP clients (axios, node-fetch, got)
-   ❌ Database drivers (beyond the SDK)
-   ❌ Parsing libraries (csv-parser, xml2js, cheerio)
-   ❌ Any other npm packages

**Use instead**:

-   ✅ Built-in JavaScript/TypeScript: `Date`, `Array`, `String`, `Object`, `Math`, `JSON`, `fetch`, etc.
-   ✅ P67 Agent SDK: For all Snowflake and Cortex interactions
-   ✅ LangGraph: For workflow orchestration

If the user's requirements seem to need an external library, find a solution using built-in JavaScript or the SDK.

## Entry Point: src/index.ts

**CRITICAL**: The `src/index.ts` file is already generated by `p67 init`. You will MODIFY this file, not create it from scratch.

### Example Structure (Generated by p67 init):

The generated `src/index.ts` looks like this:

```typescript
// src/index.ts
import { StateGraph, Annotation } from "@langchain/langgraph";
import { WorkflowSDK } from "./sdk";

// Define the state structure
const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({
        reducer: (_, right) => right,
    }),
    messages: Annotation<string[]>({
        reducer: (left, right) => left.concat(right),
    }),
    currentNode: Annotation<string>({
        reducer: (_, right) => right,
    }),
});

// CRITICAL: Function name must match the node ID from workflow_spec.json EXACTLY
// Example node - if workflow_spec.json has node id "process_data", use that exact name
async function process_data(state: typeof StateAnnotation.State) {
    console.log("Executing process_data node");
    return {
        messages: ["Process data executed"],
        currentNode: "process_data",
    };
}

// Create the workflow graph
// The string in addNode() must match both the workflow_spec.json node.id AND the function name
const workflow = new StateGraph(StateAnnotation)
    .addNode("process_data", process_data)
    .addEdge("__start__", "process_data")
    .addEdge("process_data", "__end__");

const app = workflow.compile();

// Export main function - SDK is injected by the runtime
export async function main(sdk: WorkflowSDK) {
    console.log("Starting workflow...");

    const result = await app.invoke({
        sdk: sdk,
        messages: [],
        currentNode: "",
        ...sdk.getParameters(), // If multiple configs in manifest.yaml, pass config_name: sdk.getParameters("production")
    });

    console.log("Workflow completed:", result);
    return result;
}
```

### Your Task: Modify This Template

You should:

1. **Keep** the overall structure and `main()` function signature
2. **Modify** the `StateAnnotation` to include your workflow-specific fields
3. **Replace** example nodes with your actual workflow logic
4. **Update** the graph structure (add/remove nodes and edges)
5. **Keep** the SDK integration pattern (don't change how SDK is passed)

### Running the workflow:

```bash
# Development (with watch mode)
npm run dev

# Production
npm start

# Build TypeScript
npm run build
```

## Core Technologies

### 1. Package Management: npm

-   Always use `npm` as the package manager
-   Run with: `npm start`
-   Install dependencies: `npm install`
-   Dev mode: `npm run dev`

### 2. Workflow Orchestration: LangGraph

Always use LangGraph even for deterministic workflows. Use the `Annotation` API for type-safe state management:

```typescript
import { StateGraph, Annotation } from "@langchain/langgraph";
import { WorkflowSDK } from "./sdk";

// Define state with Annotation API
const StateAnnotation = Annotation.Root({
    sdk: Annotation<WorkflowSDK>({
        reducer: (_, right) => right,
    }),
    candidates: Annotation<Array<Record<string, any>>>({
        reducer: (_, right) => right,
    }),
    analyses: Annotation<Record<string, any>>({
        reducer: (_, right) => right,
    }),
    report_path: Annotation<string>({
        reducer: (_, right) => right,
    }),
    error: Annotation<string | undefined>({
        reducer: (_, right) => right,
    }),
});

// CRITICAL: Function name must EXACTLY match the node ID from workflow_spec.json
// Example: If workflow_spec.json has a node with id "step1_analyze", name the function "step1_analyze"
async function step1_analyze(state: typeof StateAnnotation.State) {
    const { sdk } = state;

    const response = await sdk.queryCortexAnalyst("Find candidate accounts");

    if (!response.success) {
        return { error: response.error };
    }

    // Process response to extract candidates
    const candidates = response.data?.rows || [];
    return { candidates };
}

// The node ID in addNode() must match both the workflow_spec.json node.id and the function name
const workflow = new StateGraph(StateAnnotation)
    .addNode("step1_analyze", step1_analyze)
    .addEdge("__start__", "step1")
    .addEdge("step1", "__end__");

const app = workflow.compile();
```

### 3. Snowflake & Cortex Integration - Using the P67 Agent SDK

You MUST use the P67 Agent SDK for all Snowflake and Cortex interactions. Never use `snowflake-sdk` directly.

#### CRITICAL: Snowflake-Specific Patterns

**1. SQL Column Names are UPPERCASE**

Snowflake SQL always returns column names in UPPERCASE. All dictionary key lookups must use uppercase:

```typescript
// ❌ WRONG - will always return undefined
const account_id = candidate.account_id || "unknown";
const credit_change = candidate.credit_change || 0;

// ✅ CORRECT - matches SQL column names
const account_id = candidate.ACCOUNT_ID || "unknown";
const credit_change = candidate.CREDIT_CHANGE || 0;
```

**This affects:**

-   Building objects from query results
-   Reading candidate/result data in downstream steps
-   Filtering, sorting, and displaying data

**2. Pass SDK to Workflow State**

The SDK is injected into your `main()` function. Pass it to the workflow state:

```typescript
import { WorkflowSDK } from "./sdk";

export async function main(sdk: WorkflowSDK) {
    // Pass SDK to workflow via initial state
    const result = await app.invoke({
        sdk: sdk, // Inject SDK into workflow state
        candidates: [],
        analyses: {},
        report_path: "",
        error: undefined,
    });

    return result;
}
```

**3. Cortex Analyst SQL Execution Pattern**

```typescript
import { WorkflowSDK } from "./sdk";

// In a workflow node - SDK is available from state
async function analyzeStep(state: typeof StateAnnotation.State) {
    const { sdk } = state;

    // Step 1: Call Cortex Analyst to generate and execute query
    const response = await sdk.queryCortexAnalyst(
        "Find top 10 accounts with biggest credit changes",
        "@my_stage/semantic_model.yaml"
    );

    if (!response.success) {
        return { error: `Cortex Analyst failed: ${response.error}` };
    }

    // Step 2: Extract SQL and results from response
    // The response.data structure depends on the Cortex Analyst API
    // You may need to parse it to get the actual query results

    // If you need to execute custom SQL after getting Analyst's insight:
    const result = await sdk.executeQueryReadOnly(`
    SELECT account_id, account_name, credit_change
    FROM accounts
    ORDER BY credit_change DESC
    LIMIT 10
  `);

    // Step 3: Process results (columns are UPPERCASE)
    const candidates = result.rows.map((row) => ({
        ACCOUNT_ID: row.ACCOUNT_ID,
        ACCOUNT_NAME: row.ACCOUNT_NAME,
        CREDIT_CHANGE: row.CREDIT_CHANGE,
    }));

    return { candidates };
}
```

**4. Calling Cortex Agent Pattern**

```typescript
// In a workflow node - SDK is available from state
async function callAgentStep(state: typeof StateAnnotation.State) {
    const { sdk } = state;
    const account_id = "ABC123";

    // Call agent with SDK
    const response = await sdk.callCortexAgent(
        `Analyze credit changes for account ${account_id}`,
        {
            agentDatabase: "MY_DB",
            agentSchema: "MY_SCHEMA",
            agentName: "account_analyzer",
            onStream: (event) => {
                console.log(`Stream: ${event.eventName}`, event.data);
            },
        }
    );

    if (response.success) {
        console.log("Agent analysis:", response.data);
        return { analyses: { [account_id]: response.data } };
    } else {
        console.error("Agent failed:", response.error);
        console.error("Request details:", response.request);
        return { error: response.error };
    }
}
```

**5. Debug Logging Pattern**

Always log inputs/outputs and add debug prints:

```typescript
// Inside a workflow node function (e.g., "find_candidates" node from workflow_spec.json)
async function find_candidates(state: typeof StateAnnotation.State) {
    const { sdk } = state;
    const question = "Find candidate accounts";

    // Log before expensive operation
    console.log(`[index.ts:42] [find_candidates] Starting - question: ${question}`);

    // Execute operation with SDK
    const response = await sdk.queryCortexAnalyst(question);

    // Log result with details
    console.log(`[index.ts:50] [find_candidates] Completed - success: ${response.success}, has_data: ${!!response.data}`);
    if (!response.success) {
        console.log(`[index.ts:52] [find_candidates] Error: ${response.error}`);
    }

    // Add user-visible debug output
    if (response.success) {
        console.log("✅ Cortex Analyst query succeeded");
    } else {
        console.log("❌ Cortex Analyst query failed:", response.error);
    }

    return { candidates: response.data };
}
```

**CRITICAL**: The SDK handles all connection management, authentication, and URL formatting automatically. You never need to import or use `snowflake-sdk` directly.

## Workflow Design Principles

### Focus on Orchestration, Not SQL Optimization

Since Cortex Analyst handles query generation at runtime, your workflow should focus on:

1. **Step sequencing**: Define clear workflow steps
2. **State management**: Pass data between steps via LangGraph state
3. **Error handling**: Handle Analyst API failures gracefully
4. **Result processing**: Transform Analyst results for downstream steps

### Error Handling Pattern

Always handle errors gracefully without failing the entire workflow.

**IMPORTANT**: When calling `callCortexAgent`, always include the `onstream` callback to prevent timeout issues. Even if you don't need to process streaming events, provide a minimal callback like `(chunk) => {}`.

```typescript
async function analyze_step(state: WorkflowState): Promise<WorkflowState> {
    const { sdk } = state;

    const response = await sdk.callCortexAgent(question, {
        agentName: "account_analyzer",
        agentDatabase: "MY_DB",
        agentSchema: "MY_SCHEMA",
        onstream: (chunk) => {
            console.log("Streaming chunk:", chunk);
        },
    });

    if (response.success) {
        state.analyses[account_id] = {
            agent_response: response.data,
            status_code: response.status_code,
        };
    } else {
        // Store error but continue workflow
        state.analyses[account_id] = {
            error: response.error,
            status_code: response.status_code,
        };
    }

    return state;
}
```

**Benefits:**

-   Partial failures don't block report generation
-   Errors are visible in output for debugging
-   Workflow completes even with some failed steps

### State Management Best Practices

**LangGraph Annotation Pattern:**

```typescript
import { Annotation } from '@langchain/langgraph';
import { WorkflowSDK } from './sdk';

// Define state with Annotation API
const StateAnnotation = Annotation.Root({
  sdk: Annotation<WorkflowSDK>({
    reducer: (_, right) => right,
  }),
  candidates: Annotation<Array<Record<string, any>>>({  // Results from step 1
    reducer: (_, right) => right,
  }),
  analyses: Annotation<Record<string, Record<string, any>>>({  // Results from step 2 (keyed by account_id)
    reducer: (_, right) => right,
  }),
  report_path: Annotation<string>({  // Output file path
    reducer: (_, right) => right,
  }),
  error: Annotation<string | undefined>({  // Error message if workflow fails
    reducer: (_, right) => right,
  }),
});

// Use state in nodes
async function step1(state: typeof StateAnnotation.State) {
  const { sdk } = state;
  // ... workflow logic
  return { candidates: [...] };
}
```

**CRITICAL:** Object keys in state must match SQL column names (UPPERCASE):

```typescript
// Step 1: Query with SDK
async function queryStep(state: typeof StateAnnotation.State) {
    const { sdk } = state;

    const result = await sdk.executeQueryReadOnly(`
    SELECT account_id, account_name FROM accounts LIMIT 10
  `);

    // Build candidates from SQL results (columns are UPPERCASE)
    const candidates = result.rows.map((row) => ({
        ACCOUNT_ID: row.ACCOUNT_ID,
        ACCOUNT_NAME: row.ACCOUNT_NAME,
    }));

    return { candidates };
}

// Step 2: Read candidates (use UPPERCASE keys)
async function processStep(state: typeof StateAnnotation.State) {
    const { candidates } = state;

    for (const candidate of candidates) {
        const account_id = candidate.ACCOUNT_ID; // ✅ UPPERCASE
        const account_name = candidate.ACCOUNT_NAME; // ✅ UPPERCASE
    }

    return {};
}
```

### Do as Much via Cortex Analyst as Possible

**Good ✅ - Call Analyst for complex analysis:**

```typescript
async function analyze_step(state: WorkflowState): Promise<WorkflowState> {
    const { sdk } = state;

    const question = `Analyze credit changes for account ${state.account_id}`;
    const response = await sdk.queryCortexAnalyst(question);

    if (response.success) {
        return { ...state, analysis: response.data };
    } else {
        return { ...state, error: response.error };
    }
}
```

**Less Ideal ❌ - Multiple manual SQL queries:**

```typescript
// Avoid this - writing manual SQL when Analyst can handle it
async function analyze_step(state: WorkflowState): Promise<WorkflowState> {
    const { sdk } = state;
    const account_id = state.account_id;

    // Manual SQL requires expertise and maintenance
    const result = await sdk.executeQueryReadOnly(`
    SELECT SUM(credits) FROM usage WHERE account_id = ${account_id}
  `);
    // ...
}
```

## Unit Testing Requirements

### CRITICAL: Tests Must Be Isolated

Tests **MUST NEVER** access real Snowflake or Cortex services.

**Global mock in tests/setup.ts:**

```typescript
import { vi, beforeEach } from "vitest";

// Auto-mock the SDK module for all tests
beforeEach(() => {
    vi.mock("../src/sdk.ts", () => ({
        // Mock the WorkflowSDK type if needed for type checking
    }));
});

// Create mock SDK instances in your tests
function createMockSDK() {
    return {
        executeQueryReadOnly: vi.fn(async () => ({
            statement: {},
            rows: [],
        })),
        queryCortexAnalyst: vi.fn(async () => ({
            success: true,
            data: { result: "mock analysis" },
        })),
        callCortexAgent: vi.fn(async () => ({
            success: true,
            status_code: 200,
            data: { message: { content: "mock response" } },
        })),
        close: vi.fn(async () => {}),
    };
}
```

### Test structure:

```typescript
import { describe, it, expect, vi } from "vitest";
import { main } from "../src/index";

// Import or define createMockSDK helper
function createMockSDK() {
    return {
        executeQueryReadOnly: vi.fn(async () => ({
            statement: {},
            rows: [],
        })),
        queryCortexAnalyst: vi.fn(async () => ({
            success: true,
            data: { result: "mock analysis" },
        })),
        callCortexAgent: vi.fn(async () => ({
            success: true,
            status_code: 200,
            data: { message: { content: "mock response" } },
        })),
        close: vi.fn(async () => {}),
    };
}

describe("workflow", () => {
    it("should execute workflow successfully", async () => {
        // Create mock SDK
        const mockSDK = createMockSDK();

        // Mock specific behavior
        mockSDK.queryCortexAnalyst.mockResolvedValue({
            success: true,
            data: { result: "mock analysis" },
        });

        // Test main function
        const result = await main(mockSDK);

        expect(mockSDK.queryCortexAnalyst).toHaveBeenCalled();
        expect(result).toBeDefined();
    });
});
```

### Test Validation

Before completion, verify:

```bash
# Speed: < 1 second per 10 tests
time npm test

# Isolation: Tests should work without real Snowflake/Cortex connections
# (ensured by mocking SDK)
npm test

# No auth warnings
npm test 2>&1 | grep -i "browser\|keyring\|auth"
# Should return nothing
```

## Performance Considerations

1. **Runtime Trade-offs**:

    - Cortex Analyst calls add latency vs direct SQL
    - Consider caching Analyst results if appropriate
    - Monitor API rate limits

2. **When parallelization is needed** (rare):

    - Use Promise.all() for truly independent operations
    - Limit concurrent operations to ~10

3. **Measure execution time**:
    - Log start/end times for each step
    - Identify bottlenecks
    - Consider optimization if performance is critical

## Key Differences from Other Approaches

### What Makes This Different:

1. **Pre-Generated Project Structure**: `p67 init` creates all boilerplate - you just modify `src/index.ts`
2. **No External Dependencies**: Cannot use npm packages - only built-in JS/TS, SDK, and LangGraph
3. **P67 Agent SDK**: All Snowflake and Cortex interactions through unified SDK injected by runtime
4. **Runtime Analyst Calls**: Call Cortex Analyst at runtime as workflow steps
5. **Workflow-First**: Focus on orchestration, not SQL optimization
6. **Simplified Implementation**: Less SQL expertise required, more reliance on Analyst
7. **LangGraph Always**: Even for linear workflows (provides structure and error handling)
8. **Annotation API**: Use modern LangGraph `Annotation` API for type-safe state
9. **npm Package Manager**: Standard Node.js tooling (but no additional packages)
10. **TypeScript**: Type safety and modern JavaScript features
11. **Test Isolation**: Mock SDK, zero external dependencies in tests

### Common Mistakes to Avoid:

❌ **Creating project structure from scratch instead of modifying existing `src/index.ts`**
❌ **Not reading the existing code before making changes**
❌ **Installing external Node.js dependencies (lodash, axios, moment, etc.)**
❌ **Using libraries instead of built-in JavaScript features**
❌ **Adding prefixes or suffixes to function names instead of using exact node ID**
❌ **Converting node IDs to camelCase instead of keeping snake_case**
❌ Not handling Cortex Analyst/Agent API failures gracefully
❌ Overly complex workflow when simple sequential steps suffice
❌ Tests that connect to real Snowflake or Cortex services
❌ Missing error handling for SDK response objects
❌ Not validating SDK response `.success` field before using data
❌ **Using lowercase object keys for SQL results (must be UPPERCASE)**
❌ **Creating or closing the SDK in workflow code (it's injected by runtime)**
❌ **Changing the `main(sdk: WorkflowSDK)` function signature**
❌ **Not passing SDK through workflow state to all nodes**
❌ **Using old `channels` API instead of `Annotation` API for state**
❌ **Using `snowflake-sdk` directly instead of the P67 Agent SDK**
❌ **Not logging intermediate state for debugging**
❌ **Not adding debug console.log statements for visibility**
❌ **Not using async/await for all asynchronous operations**
❌ **Throwing errors from SDK methods instead of checking `.success` field**

## Package Configuration

**Note**: `package.json` and `tsconfig.json` are already generated by `p67 init`.

**CRITICAL**: You **CANNOT** add external Node.js dependencies to the workflow. The generated package.json is final.

### package.json (Pre-Generated - DO NOT MODIFY)

The generated `package.json` includes all allowed dependencies:

```json
{
    "name": "my-workflow",
    "version": "0.1.0",
    "type": "module",
    "main": "src/index.ts",
    "scripts": {
        "start": "tsx src/index.ts",
        "dev": "tsx --watch src/index.ts",
        "build": "tsc",
        "test": "vitest"
    },
    "dependencies": {
        "@langchain/langgraph": "^0.2.0"
    },
    "devDependencies": {
        "@types/node": "^20.0.0",
        "typescript": "^5.0.0",
        "tsx": "^4.0.0",
        "vitest": "^1.0.0"
    }
}
```

**DO NOT add any dependencies.** Use:

-   Built-in JavaScript/TypeScript features (Date, Array, String, Object, Math, JSON, fetch, Promise, etc.)
-   P67 Agent SDK (provided by runtime)
-   LangGraph (already included)

**Examples of handling common needs WITHOUT external libraries**:

**Date manipulation**: Use built-in `Date` object

```typescript
// Get date 7 days ago
const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
const dateString = sevenDaysAgo.toISOString().split("T")[0]; // YYYY-MM-DD
```

**Array operations**: Use built-in Array methods

```typescript
// Group by, filter, map, reduce - all built-in
const grouped = items.reduce((acc, item) => {
    acc[item.category] = acc[item.category] || [];
    acc[item.category].push(item);
    return acc;
}, {});
```

**HTTP requests**: Use built-in `fetch`

```typescript
// No need for axios
const response = await fetch("https://api.example.com/data");
const data = await response.json();
```

**String manipulation**: Use built-in String methods

```typescript
// No need for lodash
const slug = str
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^\w-]/g, "");
```

### tsconfig.json (Pre-Generated)

The generated `tsconfig.json` is already configured correctly:

```json
{
    "compilerOptions": {
        "target": "ES2022",
        "module": "ESNext",
        "moduleResolution": "bundler",
        "strict": true,
        "esModuleInterop": true,
        "skipLibCheck": true,
        "resolveJsonModule": true,
        "outDir": "./dist",
        "rootDir": "./src"
    },
    "include": ["src/**/*"],
    "exclude": ["node_modules", "dist", "tests"]
}
```

**Do not modify**: This configuration is optimized for P67 workflows.

## Final Checklist

Before completion:

-   [ ] **User has run `p67 init` to generate project structure**
-   [ ] Read existing `src/index.ts` to understand the template
-   [ ] OVERVIEW.md created and approved
-   [ ] **Modified `src/index.ts` with workflow-specific logic**
-   [ ] **StateAnnotation updated with workflow-specific fields**
-   [ ] **Workflow nodes implemented with actual logic (not example code)**
-   [ ] **Function names EXACTLY match node IDs from workflow_spec.json (no prefixes/suffixes)**
-   [ ] **Graph structure updated (nodes and edges)**
-   [ ] **SDK passed to workflow via initial state (pattern unchanged)**
-   [ ] **NO external dependencies added (used only built-in JavaScript + SDK + LangGraph)**
-   [ ] All Snowflake queries use `sdk.executeQueryReadOnly()`
-   [ ] Cortex Analyst calls use `sdk.queryCortexAnalyst()`
-   [ ] Cortex Agent calls use `sdk.callCortexAgent()`
-   [ ] Error handling for SDK methods that return response objects
-   [ ] **All object keys use UPPERCASE for SQL results**
-   [ ] **State logging added for debugging (JSONL files)**
-   [ ] **Debug console.log statements added for visibility**
-   [ ] **All async operations use async/await**
-   [ ] Additional files created in src/ as needed (utils.ts, etc.)
-   [ ] **Verified no external libraries used - only built-in JS/TS + SDK + LangGraph**
-   [ ] Tests created for workflow logic (optional)
-   [ ] Tests isolated (mock SDK, no real Snowflake/Cortex access)
-   [ ] Tests pass speed validation (< 1s per 10 tests)
-   [ ] Tests pass isolation validation (no external dependencies)
-   [ ] Performance measured and acceptable
-   [ ] README.md updated with workflow-specific instructions
-   [ ] End-to-end workflow executes successfully with `npm start`
