# Creating a Workflow with p67

This guide walks you through the complete process of creating, testing, and implementing a workflow using the p67 system.

## Overview

The p67 workflow creation process consists of 7 main steps:

1. **Define Workflow** - Create the workflow specification
2. **Define Workflow Tests** - Generate comprehensive test cases
3. **Create Semantic Views** - Set up data access layer
4. **Generate Workflow Code** - Implement the workflow in TypeScript
5. **Visualize & Edit** - Use the workflow editor to visualize and refine
6. **Test** - Run unit tests and integration tests
7. **Deploy** - Deploy to production

## Prerequisites

- Snowflake account with appropriate permissions
- Node.js and npm installed
- Python 3.x installed (for workflow editor)
- Claude/Cortex CLI access

## Step-by-Step Instructions

### Step 1: Navigate to Your Project Directory

```bash
cd /path/to/your/workflow/project
```

### Step 2: Start Cortex Interactive Session

```bash
cortex
```

This launches the interactive Cortex CLI where you can run workflow design commands.

### Step 3: Define the Workflow Specification

In the Cortex prompt, run:

```bash
/define-workflow
```

**What this does:**
- Launches an interactive workflow design consultant
- Guides you through requirements gathering
- Helps you define nodes, edges, and variables
- Generates `workflow_spec.json`

**Tips:**
- Answer questions one at a time
- Be specific about your workflow goals
- Think through both happy paths and edge cases
- The consultant will confirm your understanding before proceeding

**Output:** `./workflow_spec.json`

### Step 4: Define Workflow Test Cases

In the Cortex prompt, run:

```bash
/define-workflow-test
```

**What this does:**
- Reads your `workflow_spec.json`
- Identifies all possible execution paths
- Generates comprehensive test cases
- Creates `workflow_test.md` with detailed test specifications

**The test specification includes:**
- Test case identification (TC-1, TC-2, etc.)
- Initial workflow variables
- External data requirements
- Execution path with variable tracking
- Final workflow variables

**Output:** `./workflow_test.md`

### Step 5: Create Semantic Views

In the Cortex prompt, run:

```bash
/create-semantic-views
```

**What this does:**
- Analyzes query_node requirements in your workflow
- Discovers existing Snowflake semantic views
- Proposes new semantic views if needed
- Generates YAML definitions for new semantic views
- Creates semantic views in Snowflake

**Outputs:**
- `./semantic_views.yaml` - Catalog of all semantic views (existing + new)
- `./new_semantic_views/*.yaml` - YAML definitions for new views
- Semantic views created in Snowflake database `EGS`, schema `TEMP`

**What gets created:**
The command will:
1. Query your Snowflake account for existing semantic views
2. Evaluate which queries can be answered
3. Create a catalog in `semantic_views.yaml`
4. Generate YAML files for new semantic views
5. Upload YAMLs to Snowflake stage
6. Create semantic views using `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`

### Step 6: Generate Workflow Implementation Code

In the Cortex prompt, run:

```bash
/generate-workflow-code
```

**What this does:**
- Reads `workflow_spec.json` and `semantic_views.yaml`
- Generates TypeScript implementation using LangGraph
- Creates project structure with proper organization
- Implements all workflow nodes as separate step files
- Adds Cortex Analyst integration
- Creates unit tests with proper mocking

**Project structure created:**
```
project/
├── .env                    # Snowflake credentials (gitignored)
├── .env.template          # Template with examples
├── .gitignore
├── package.json           # npm project config
├── tsconfig.json          # TypeScript compiler config
├── README.md              # Setup and usage instructions
├── src/                   # Source directory
│   ├── index.ts           # Entry point
│   ├── config.ts          # Configuration from .env
│   ├── utils.ts           # Shared utilities (Cortex Analyst caller)
│   ├── workflow.ts        # LangGraph workflow definition
│   └── steps/             # Workflow step implementations
│       ├── [node1].ts     # One file per workflow node
│       ├── [node2].ts
│       └── [node3].ts
├── state/                 # JSONL debug logs
└── tests/                 # Unit tests
    ├── setup.ts           # Global mocks
    ├── [node1].test.ts
    └── ...
```

**Key files explained:**
- **src/index.ts** - Main entry point that starts the workflow
- **src/workflow.ts** - LangGraph workflow graph definition
- **src/steps/** - Each workflow node has its own TypeScript file
- **src/utils.ts** - Contains `query_cortex_analyst()` and logging utilities
- **state/** - JSONL files for debugging (logs inputs/outputs per step)

### Step 7: Install Dependencies

Exit the Cortex session and install Node.js dependencies:

```bash
# Exit cortex
exit

# Install dependencies
npm install
```

### Step 8: Configure Snowflake Connection

Edit the `.env` file with your Snowflake credentials:

```bash
# Copy template
cp .env.template .env

# Edit with your credentials
nano .env
```

**Required configuration:**
```env
SNOWFLAKE_ACCOUNT=your-account-identifier
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_ROLE=your-role
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=your-schema
```

### Step 9: Visualize and Edit the Workflow

The workflow editor allows you to visualize your workflow graph and edit the implementation code.

#### Step 9.1: Start the Workflow Server

From your project root, navigate to the workflow editor directory and start the server:

```bash
cd tools/workflow-editor

# Using Python directly
python3 workflow_server.py

# Or using uv (if installed)
uv run workflow_server.py
```

The server will start on `http://localhost:8000`

#### Step 9.2: Open the Workflow Browser

Open your web browser and navigate to:

```
http://localhost:8000/workflow_browser.html
```

#### Step 9.3: Use the Workflow Editor

The workflow browser provides:

**Left Panel: Workflow Visualization**
- Mermaid diagram of your workflow graph
- Shows all nodes and edges
- Highlights decision nodes with different colors
- Edge labels show routing conditions

**Right Panel: Code Editor**
- Select any node to view its implementation
- Edit TypeScript code directly
- Changes are saved back to the `src/steps/` files
- Syntax highlighting for TypeScript

**Features:**
- **Navigate**: Click on nodes to jump to their implementation
- **Edit**: Modify node logic, fix issues, add features
- **Visualize**: Understand workflow structure at a glance
- **Debug**: Identify which nodes are involved in specific paths

**Workflow diagram colors:**
- Green: Start/End nodes
- Yellow: Decision nodes (branches)
- Blue: Action/Query nodes

### Step 10: Run Unit Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

**Test validation checklist:**
- Tests complete in < 1 second per 10 tests
- Tests work offline (without `.env` file)
- No authentication warnings
- All tests pass

### Step 11: Run the Workflow

```bash
# Development mode (with hot reload)
npm run dev

# Production mode
npm start

# Build TypeScript (if needed)
npm run build
```

### Step 12: Review Debug Logs

Check the `state/` directory for JSONL debug logs:

```bash
# View logs for a specific step
cat state/[step_name].jsonl | jq '.'

# View all logs
cat state/*.jsonl | jq '.'
```

Each log entry includes:
- `step_name` - Which node executed
- `line_ref` - Source code location (file:line)
- `inputs` - Input parameters to the step
- `outputs` - Results from the step
- `timestamp` - When the step executed

## Workflow Design Best Practices

### Node Design

1. **Action Nodes** - For side effects (payments, emails, updates)
   - Exactly one incoming edge, one outgoing edge
   - Calls `action_[name]([parameters])`

2. **Query Nodes** - For reading data via Cortex Analyst
   - Exactly one incoming edge, one outgoing edge
   - Calls `query([question])` on semantic views
   - Populates workflow variables with external data

3. **Decision Nodes** - For branching logic
   - One incoming edge, multiple outgoing edges
   - Each branch has `label` and `condition` (text description)
   - Conditions reference workflow variables

4. **Human Nodes** - For human-in-the-loop tasks
   - Exactly one incoming edge, one outgoing edge
   - Calls `human([role], [task_description])`

### Variable Management

- Variables flow through the workflow state
- Each node can read inputs and write outputs via mapping functions
- Use clear, descriptive variable names
- Document variable data types in the spec

### Error Handling

- Workflows should handle both happy paths and error cases
- Use try-catch blocks in step implementations
- Log errors to state for debugging
- Consider graceful degradation where appropriate

## Tracing and Debugging

### Built-in Tracing

The p67 system provides built-in tracing through:

1. **State Logging** (`state/*.jsonl` files)
   - Every step logs inputs/outputs
   - Includes source code references
   - Captures REST API requests/responses with headers

2. **Console Debug Output**
   - Each step prints progress messages
   - Shows counts, summaries, and results
   - Example: `✅ Found 23 candidate accounts`

3. **LangGraph State Management**
   - Full workflow state preserved between steps
   - State includes all variables at each point
   - Can inspect state at any node

### How to Track Execution

**Question: Which nodes were called?**
- Check console output for step-by-step execution
- Review `state/*.jsonl` for complete execution log
- Each JSONL entry shows the step name and when it ran

**Question: What were the input/output parameters?**
- State logs include `inputs` and `outputs` fields
- Console output shows key values during execution
- LangGraph state shows variable evolution

**Question: What were the graph states?**
- The `WorkflowState` interface defines all state variables
- Each step returns updated state
- State logs capture state before and after each node

### Example Tracing Output

**Console output:**
```
Starting workflow...
[step1_find_candidates] Calling Cortex Analyst...
✅ Found 23 candidate accounts
   Gainers: 15
   Losers: 8
[step2_analyze] Analyzing account ACC-001...
✅ Analysis complete for ACC-001
...
Workflow completed: { report_path: './output/report.md' }
```

**State log (`state/step1_find_candidates.jsonl`):**
```json
{"step_name":"step1_find_candidates","line_ref":"step1.ts:42","inputs":{"question":"Find accounts with significant credit changes"},"outputs":{"status":"calling_analyst"},"timestamp":"2026-01-03T10:15:30.123Z"}
{"step_name":"step1_find_candidates","line_ref":"step1.ts:90","inputs":{"num_rows":23},"outputs":{"candidates":[{"ACCOUNT_ID":"ACC-001","CREDIT_CHANGE":1500},...]},"timestamp":"2026-01-03T10:15:35.456Z"}
```

### Advanced Debugging

For more detailed tracing, you can:

1. **Add custom log statements** in step files:
   ```typescript
   console.log('Debug: Processing candidate', candidate.ACCOUNT_ID);
   log_state({ step_name: 'my_step', inputs: { x }, outputs: { y } });
   ```

2. **Use LangGraph's built-in checkpointing** (optional):
   ```typescript
   const checkpointer = new MemorySaver();
   const app = workflow.compile({ checkpointer });
   ```

3. **Inspect Cortex Analyst SQL**:
   - State logs include full REST API requests/responses
   - Extract SQL statements from Analyst responses
   - Review generated queries for optimization

## Troubleshooting

### Common Issues

**Issue: "workflow_spec.json not found"**
- Solution: Run `/define-workflow` first

**Issue: "Semantic view not found"**
- Solution: Run `/create-semantic-views` to create required views
- Check Snowflake permissions

**Issue: "Tests fail with authentication errors"**
- Solution: Ensure tests are properly mocked
- Check `tests/setup.ts` for global mocks

**Issue: "Column 'account_id' is undefined"**
- Solution: Use UPPERCASE column names (Snowflake returns uppercase)
- Change `candidate.account_id` to `candidate.ACCOUNT_ID`

**Issue: "SSL certificate verification failed"**
- Solution: Convert account identifier to URL format
- Replace underscores with hyphens, use lowercase

**Issue: "Workflow editor won't load"**
- Solution: Ensure workflow_server.py is running on port 8000
- Check that you're accessing `http://localhost:8000/workflow_browser.html`

## File Reference

### Core Workflow Files

| File | Purpose |
|------|---------|
| `workflow_spec.json` | Workflow specification (nodes, edges, variables) |
| `workflow_test.md` | Test cases covering all execution paths |
| `semantic_views.yaml` | Catalog of semantic views |
| `new_semantic_views/*.yaml` | YAML definitions for new semantic views |

### Implementation Files

| File | Purpose |
|------|---------|
| `src/index.ts` | Entry point that starts the workflow |
| `src/workflow.ts` | LangGraph workflow definition |
| `src/steps/*.ts` | Individual node implementations |
| `src/utils.ts` | Cortex Analyst integration, logging |
| `src/config.ts` | Configuration from `.env` |

### Testing Files

| File | Purpose |
|------|---------|
| `tests/setup.ts` | Global test mocks |
| `tests/*.test.ts` | Unit tests for each step |

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Snowflake credentials (not committed) |
| `.env.template` | Template for credentials |
| `package.json` | npm dependencies and scripts |
| `tsconfig.json` | TypeScript compiler configuration |

## Next Steps

After creating your workflow:

1. **Review the generated code** - Understand the implementation
2. **Run tests** - Verify all tests pass
3. **Execute the workflow** - Test with real data
4. **Monitor logs** - Check state logs for debugging
5. **Iterate** - Refine the workflow based on results
6. **Deploy** - Move to production when ready

## Getting Help

- Check the Cortex CLI documentation: Run `cortex help`
- Review command-specific help: Run `/[command-name] --help` in Cortex
- Inspect example workflows in `p67/example_workflows/`
- Review LangGraph documentation for advanced workflow patterns

## Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Snowflake Cortex Analyst Documentation](https://docs.snowflake.com/en/user-guide/cortex-analyst)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
