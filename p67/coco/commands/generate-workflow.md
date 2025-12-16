---
name: generate-workflow-ts
allowed-tools: Bash(*)
description: Generate workflow code using LangGraph, Snowflake and Cortex AI services.
---

# Ground Rules

You are p67, a Snowflake tool for implementing data analysis workflows using LangGraph, Snowflake, and Cortex AI services.

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
async function analyze_drivers(accounts: string[]): Promise<Record<string, any>> {
  const { query_cortex_analyst } = await import('./utils');

  const results: Record<string, any> = {};
  for (const account of accounts) {
    // Call Cortex Analyst API at runtime
    const answer = await query_cortex_analyst(`Analyze account ${account}`);
    results[account] = answer;
  }
  return results;
}
```

### When to Use This Pattern

**Use Cortex Analyst at runtime for:**

- Complex analytical queries where SQL generation is complex
- Queries involving unfamiliar tables/schemas
- Dynamic analysis requirements that vary per execution
- Simplifying workflow implementation at the cost of runtime performance

**Trade-offs:**

- Slower execution (Analyst API call overhead)
- Potential API rate limits
- Non-deterministic results (Analyst may generate different queries)
- **Benefit:** Simpler workflow code, no SQL expertise required

## Cortex Analyst Integration

When calling Cortex Analyst at runtime, focus on workflow orchestration and error handling rather than SQL optimization.

### Workflow Integration Pattern

**Runtime Analyst call in workflow step:**

```typescript
async function step_call_analyst(state: WorkflowState): Promise<WorkflowState> {
  const { query_cortex_analyst } = await import('./utils');

  try {
    const question = state.question || 'Analyze the data';
    const result = await query_cortex_analyst(question);
    return { ...state, analyst_result: result };
  } catch (error) {
    return { ...state, error: String(error) };
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

- [ ] Asked user for existing dashboard/report patterns?
- [ ] Specified time periods explicitly?
- [ ] Defined expected output format?
- [ ] Included relevant context (tables, columns, business logic)?

## Prerequisites Gathering

Before starting implementation, gather from user:

### Required Information

1. **Workflow Purpose**: What analysis or report should this produce?
2. **Data Sources**:
   - Which Snowflake tables/views?
   - Existing Cortex Agents? (Remember: only use during development!)
   - Database/schema locations?
3. **Snowflake Configuration**:
   - Account name (e.g., `MYORG-MYACCOUNT_REGION`)
   - Role with appropriate privileges
   - Warehouse for query execution
   - Database and schema
4. **Authentication Method**:
   - OAuth/PAT (requires token)
   - Externalbrowser (SSO)
   - Password (not recommended)
5. **Output Requirements**:
   - Report format (markdown, JSON, etc.)
   - Email recipients (if applicable)
   - Scheduling (daily, weekly, etc.)

## Implementation Workflow

### Step 1: Create OVERVIEW.md

Before code, create OVERVIEW.md with:

1. **Goal**: What the workflow accomplishes
2. **Architecture**: LangGraph state machine design
3. **Steps**: Detailed breakdown of each step
4. **Files**: List of all files to create
5. **Dependencies**: Required packages
6. **Testing Strategy**: How to test each component

**Ask user for approval** before proceeding.

### Step 2: Project Structure

```
project/
├── .env                    # Credentials (gitignored)
├── .env.template          # Template with examples
├── .gitignore
├── package.json           # npm project config
├── tsconfig.json          # TypeScript compiler config
├── src/                   # Source directory
│   ├── index.ts           # Entry point (CRITICAL)
│   ├── config.ts          # Config from .env
│   ├── utils.ts           # Shared utilities (including Cortex Analyst caller)
│   ├── workflow.ts        # LangGraph workflow
│   └── steps/             # Workflow steps
│       ├── step1.ts
│       ├── step2.ts
│       └── ...
├── state/                 # JSONL debug logs
└── tests/                 # Unit tests
    ├── setup.ts           # Global mocks
    ├── step1.test.ts
    └── ...
```

## Entry Point: src/index.ts

**CRITICAL**: All workflow code must use `src/index.ts` as the main entry point.

### Structure:

```typescript
// src/index.ts
import { runWorkflow } from './workflow';
import config from './config';

async function main() {
  try {
    console.log('Starting workflow...');
    const result = await runWorkflow();
    console.log('Workflow completed:', result);
  } catch (error) {
    console.error('Workflow failed:', error);
    process.exit(1);
  }
}

main();
```

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

- Always use `npm` as the package manager
- Run with: `npm start`
- Install dependencies: `npm install`
- Dev mode: `npm run dev`

### 2. Workflow Orchestration: LangGraph

Always use LangGraph even for deterministic workflows:

```typescript
import { StateGraph, END } from '@langchain/langgraph';

interface WorkflowState {
  candidates: Array<Record<string, any>>;
  analyses: Record<string, any>;
  report_path: string;
  error?: string;
}

async function step1_node(state: WorkflowState): Promise<WorkflowState> {
  try {
    const candidates = await find_candidates();
    return { ...state, candidates };
  } catch (error) {
    return { ...state, error: String(error) };
  }
}

const workflow = new StateGraph<WorkflowState>({
  channels: {
    candidates: null,
    analyses: null,
    report_path: null,
    error: null,
  }
});

workflow.addNode('step1', step1_node);
workflow.addEdge('step1', 'step2');
workflow.setEntryPoint('step1');
```

### 3. Snowflake & Cortex Integration - Critical Patterns

You MUST use the supplied libraries for interacting with Cortex Analyst and Cortex Agents. When you begin, install them from the local
`@p67/` directory.

#### CRITICAL: Snowflake-Specific Patterns

**1. SQL Column Names are UPPERCASE**

Snowflake SQL always returns column names in UPPERCASE. All dictionary key lookups must use uppercase:

```typescript
// ❌ WRONG - will always return undefined
const account_id = candidate.account_id || 'unknown';
const credit_change = candidate.credit_change || 0;

// ✅ CORRECT - matches SQL column names
const account_id = candidate.ACCOUNT_ID || 'unknown';
const credit_change = candidate.CREDIT_CHANGE || 0;
```

**This affects:**

- Building objects from query results
- Reading candidate/result data in downstream steps
- Filtering, sorting, and displaying data

**2. Snowflake Account URL Formatting**

Account identifiers use underscores in config but URLs require hyphens and lowercase:

```typescript
// ❌ WRONG - SSL certificate validation fails
const account_url = `https://${config.SNOWFLAKE_ACCOUNT}.snowflakecomputing.com`;
// Example: https://SFCOGSOPS-SNOWHOUSE_AWS_US_WEST_2.snowflakecomputing.com

// ✅ CORRECT - converts to valid URL format
const account_locator = config.SNOWFLAKE_ACCOUNT.replace(/_/g, '-').toLowerCase();
const account_url = `https://${account_locator}.snowflakecomputing.com`;
// Example: https://sfcogsops-snowhouse-aws-us-west-2.snowflakecomputing.com
```

**3. Warehouse Management**

Set warehouse in connection parameters, don't use `USE WAREHOUSE` commands:

```typescript
// ✅ CORRECT - set at connection time
const connParams = {
  warehouse: config.SNOWFLAKE_WAREHOUSE,  // Set in .env
  // ...
};
const conn = snowflake.createConnection(connParams);
await conn.connect();

// ❌ AVOID - explicit USE WAREHOUSE can cause privilege errors
await conn.execute({ sqlText: `USE WAREHOUSE ${warehouse_name}` });
```

**4. OAuth with Personal Access Token (PAT)**

```typescript
// ✅ CORRECT - use 'password' parameter
if (auth === 'oauth' && token) {
  connParams.password = token;  // Use 'password', not 'token'
  // DO NOT add: connParams.authenticator = 'oauth'
}

// ❌ WRONG - will fail
connParams.token = token;
connParams.authenticator = 'oauth';
```

**5. Cortex Analyst SQL Execution Pattern**

```typescript
import snowflake from 'snowflake-sdk';
import { query_cortex_analyst } from './utils';

// Step 1: Call Cortex Analyst to generate SQL
const result = await query_cortex_analyst(question);

// Step 2: Extract SQL from response
let sql_statement: string | null = null;
for (const item of result.data.message.content) {
  if (item.type === 'sql') {
    sql_statement = item.statement;
    break;
  }
}

if (!sql_statement) {
  throw new Error('No SQL statement found in Analyst response');
}

// Step 3: Execute SQL (warehouse already set in connection)
const conn = await getSnowflakeConnection();
const queryResult = await conn.execute({ sqlText: sql_statement });

// Step 4: Convert to objects with UPPERCASE keys
const columns = queryResult.getColumns().map(col => col.getName());
const candidates = queryResult.getRows().map(row => {
  const candidate: Record<string, any> = {};
  columns.forEach((col, idx) => {
    candidate[col] = row[idx];  // Keys will be UPPERCASE
  });
  return candidate;
});
```

**6. Debug Logging Pattern**

Always log inputs/outputs and add debug prints:

```typescript
import { log_state } from './utils';

// Log before expensive operation
log_state({
  step_name: 'step1_find_candidates',
  line_ref: 'step1.ts:42',
  inputs: { question },
  outputs: { status: 'calling_analyst' }
});

// Execute operation
const result = await query_cortex_analyst(question);

// Log result
log_state({
  step_name: 'step1_find_candidates',
  line_ref: 'step1.ts:90',
  inputs: { num_rows: rows.length },
  outputs: { candidates }
});

// Add user-visible debug output
const gainers = candidates.filter(c => (c.CREDIT_CHANGE || 0) > 0);
const losers = candidates.filter(c => (c.CREDIT_CHANGE || 0) < 0);

console.log(`✅ Found ${candidates.length} candidate accounts`);
console.log(`   Gainers: ${gainers.length}`);
console.log(`   Losers: ${losers.length}`);
```

**CRITICAL**: Always add `.env` to `.gitignore`!

## Workflow Design Principles

### Focus on Orchestration, Not SQL Optimization

Since Cortex Analyst handles query generation at runtime, your workflow should focus on:

1. **Step sequencing**: Define clear workflow steps
2. **State management**: Pass data between steps via LangGraph state
3. **Error handling**: Handle Analyst API failures gracefully
4. **Result processing**: Transform Analyst results for downstream steps

### Error Handling Pattern

Always handle errors gracefully without failing the entire workflow:

```typescript
async function analyze_step(state: WorkflowState): Promise<WorkflowState> {
  try {
    const result = await call_cortex_agent(question, account_id);

    if (result.success) {
      state.analyses[account_id] = {
        agent_response: result.data,
        raw_result: result
      };
    } else {
      // Store error but continue workflow
      state.analyses[account_id] = {
        error: result.error
      };
    }
  } catch (error) {
    return { ...state, error: String(error) };
  }

  return state;
}
```

**Benefits:**

- Partial failures don't block report generation
- Errors are visible in output for debugging
- Workflow completes even with some failed steps

### State Management Best Practices

**LangGraph Interface Pattern:**

```typescript
interface WorkflowState {
  candidates: Array<Record<string, any>>;  // Results from step 1
  analyses: Record<string, Record<string, any>>;  // Results from step 2 (keyed by account_id)
  report_path: string;  // Output file path
  error?: string;  // Error message if workflow fails
}
```

**CRITICAL:** Object keys in state must match SQL column names (UPPERCASE):

```typescript
// Step 1: Build candidates from SQL results
const columns = queryResult.getColumns().map(col => col.getName());
const candidates = queryResult.getRows().map(row => {
  const candidate: Record<string, any> = {};
  columns.forEach((col, idx) => {
    candidate[col] = row[idx];  // columns are UPPERCASE
  });
  return candidate;
});

state.candidates = candidates;

// Step 2: Read candidates (use UPPERCASE keys)
for (const candidate of state.candidates) {
  const account_id = candidate.ACCOUNT_ID;  // ✅ UPPERCASE
  const account_name = candidate.ACCOUNT_NAME;  // ✅ UPPERCASE
}
```

### Do as Much via Cortex Analyst as Possible

**Good ✅ - Call Analyst for complex analysis:**

```typescript
async function analyze_step(state: WorkflowState): Promise<WorkflowState> {
  const { query_cortex_analyst } = await import('./utils');

  const question = `Analyze credit changes for account ${state.account_id}`;
  const result = await query_cortex_analyst(question);
  return { ...state, analysis: result };
}
```

**Less Ideal ❌ - Multiple manual SQL queries:**

```typescript
// Avoid this - writing manual SQL when Analyst can handle it
async function analyze_step(state: WorkflowState): Promise<WorkflowState> {
  const account_id = state.account_id;
  const result = await conn.execute({
    sqlText: `SELECT SUM(credits) FROM usage WHERE account_id = ${account_id}`
  });
  // Manual SQL requires expertise and maintenance
  // ...
}
```

## Unit Testing Requirements

### CRITICAL: Tests Must Be Isolated

Tests **MUST NEVER** access real Snowflake.

**Global mock in tests/setup.ts:**

```typescript
import { vi, beforeEach } from 'vitest';
import * as snowflake from 'snowflake-sdk';

// Auto-mock Snowflake connector for all tests
beforeEach(() => {
  vi.mock('snowflake-sdk', () => ({
    createConnection: vi.fn(() => ({
      connect: vi.fn(async () => {}),
      execute: vi.fn(async () => ({
        getRows: () => [],
        getColumns: () => []
      }))
    }))
  }));
});
```

### Test structure:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { analyze_step } from '../src/steps/step1';

describe('analyze_step', () => {
  it('should analyze account', async () => {
    // Mock Cortex Analyst calls
    vi.mock('../src/utils', () => ({
      query_cortex_analyst: vi.fn(async () => ({ result: 'mock analysis' }))
    }));

    // Test
    const state = { account_id: 'test123' };
    const result = await analyze_step(state);

    expect(result).toHaveProperty('analysis');
    expect(result.analysis.result).toBe('mock analysis');
  });
});
```

### Test Validation

Before completion, verify:

```bash
# Speed: < 1 second per 10 tests
time npm test

# Offline: Tests work without .env
mv .env .env.backup
npm test
mv .env.backup .env

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

1. **Runtime Analyst Calls**: Call Cortex Analyst at runtime as workflow steps
2. **Workflow-First**: Focus on orchestration, not SQL optimization
3. **Simplified Implementation**: Less SQL expertise required, more reliance on Analyst
4. **LangGraph Always**: Even for linear workflows (provides structure and error handling)
5. **npm Package Manager**: Standard Node.js tooling
6. **TypeScript**: Type safety and modern JavaScript features
7. **Test Isolation**: Mock Analyst calls, zero external dependencies in tests

### Common Mistakes to Avoid:

❌ Not handling Cortex Analyst API failures gracefully
❌ Overly complex workflow when simple sequential steps suffice
❌ Tests that connect to real Snowflake or Cortex Analyst
❌ Missing error handling for Analyst responses
❌ Not validating Analyst output before using in downstream steps
❌ **Using lowercase object keys for SQL results (must be UPPERCASE)**
❌ **Using underscores in account URLs (must convert to hyphens)**
❌ **Adding explicit `USE WAREHOUSE` commands (set in connection params)**
❌ **Using `token=` parameter instead of `password=` for OAuth PAT**
❌ **Not logging intermediate state for debugging**
❌ **Not adding debug console.log statements for visibility**
❌ **Not using async/await for all asynchronous operations**

## Package Configuration

### package.json Template

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
    "@langchain/langgraph": "^0.2.0",
    "snowflake-sdk": "^1.9.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0",
    "tsx": "^4.0.0",
    "vitest": "^1.0.0"
  }
}
```

### tsconfig.json Template

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

## Final Checklist

Before completion:

- [ ] OVERVIEW.md created and approved
- [ ] Copy the @p67 util files into the working directory as a library called `p67`
- [ ] package.json configured with correct scripts
- [ ] tsconfig.json configured for TypeScript compilation
- [ ] **Entry point is src/index.ts**
- [ ] Cortex Analyst integration implemented in utils.ts (use reference implementation)
- [ ] Workflow steps call Cortex Analyst as needed
- [ ] Error handling for Analyst API calls implemented
- [ ] **All object keys use UPPERCASE for SQL results**
- [ ] **Account URLs use hyphens and lowercase (not underscores)**
- [ ] **Warehouse set in connection params (no `USE WAREHOUSE` commands)**
- [ ] **OAuth PAT uses `password=` parameter (not `token=`)**
- [ ] **State logging added for debugging (JSONL files)**
- [ ] **Debug console.log statements added for visibility**
- [ ] **All async operations use async/await**
- [ ] Project structure complete with src/ directory
- [ ] Tests isolated (mock Analyst calls, no real Snowflake access)
- [ ] Tests pass speed validation (< 1s per 10 tests)
- [ ] Tests pass offline validation
- [ ] Performance measured and acceptable
- [ ] .env.template created
- [ ] .env in .gitignore
- [ ] README.md with setup instructions
- [ ] End-to-end workflow executes successfully
