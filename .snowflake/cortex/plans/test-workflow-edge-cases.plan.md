---
name: "test workflow edge cases"
created: "2026-03-16T21:11:41.942Z"
status: pending
---

# Plan: Test Workflow Edge Cases for Graph Visualization

## Context

The SPCS-deployed frostsight workflows have no workflow graphs because they were never built with `p67 build`, which is the step that auto-extracts LangGraph topology into `graph.json`. We need to create test workflows that exercise every graph resolution path and deploy them through the proper pipeline.

## Graph Resolution Paths (from graph.ts)

```
GET /:workflowId/graph
  1. manifest.yaml has graph: section  --> return manifest graph
  2. graph.json exists in storagePath  --> return graph.json (auto-extracted)
  3. Neither exists                    --> return { graph: null }
```

## Workflow Structure (per existing conventions)

Each workflow will follow the structure established in workflows/trigger/:

```
workflows/test/<name>/
  p67.yml           # buildDir: build
  manifest.yaml     # name, visibility, params, config
  package.json      # dependencies (langgraph or not)
  src/
    index.ts        # entry point: export async function main(sdk)
    sdk.ts          # WorkflowSDK type shim (copied from existing)
```

## Workflows to Create

### 1. `GRAPH_AUTO_EXTRACT` -- Auto-extracted LangGraph graph

**Purpose:** Validates that `p67 build` auto-extracts `graph.json` from a LangGraph `StateGraph.compile()` call.

- **Location:** `workflows/test/graph_auto_extract/`
- **manifest.yaml:** `name: GRAPH_AUTO_EXTRACT`, no `graph:` section, `config: []`
- **Logic:** Simple 3-node LangGraph: `validate_input` -> `process_data` -> `format_output`
- **Expected result after build:** `build/graph.json` exists with 5 nodes (start, 3 action, end) and 4 edges
- **package.json:** includes `@langchain/langgraph`

### 2. `GRAPH_MANUAL` -- Manual graph definition in manifest

**Purpose:** Validates the manifest `graph:` path. No LangGraph dependency at all.

- **Location:** `workflows/test/graph_manual/`
- **manifest.yaml:** `name: GRAPH_MANUAL`, with full `graph:` section defining nodes/edges
- **Logic:** Plain imperative workflow (no LangGraph import). Just reads params, does a string transform, returns result.
- **Expected result:** Graph served from manifest, no `graph.json` needed
- **package.json:** only `zod` (no langgraph)

### 3. `GRAPH_NONE` -- No graph at all

**Purpose:** Validates the null graph edge case. The UI should handle this gracefully (no graph tab, or empty state).

- **Location:** `workflows/test/graph_none/`
- **manifest.yaml:** `name: GRAPH_NONE`, no `graph:` section, `config: []`
- **Logic:** Simplest possible workflow -- echoes parameters back.
- **Expected result:** `GET /graph` returns `{ graph: null }`
- **package.json:** only `zod` (no langgraph)

### 4. `GRAPH_HITL` -- HITL/Interrupt with LangGraph

**Purpose:** Tests graph extraction for a workflow that uses `sdk.interrupt()` inside a LangGraph node. This is a key edge case because the interrupt pattern involves a human\_node concept.

- **Location:** `workflows/test/graph_hitl/`
- **manifest.yaml:** `name: GRAPH_HITL`, no `graph:` section (rely on auto-extraction)
- **Logic:** LangGraph with 3 nodes: `prepare_report` -> `request_approval` (calls sdk.interrupt) -> `finalize_report`. The interrupt node pauses execution and waits for human input.
- **Expected result:** Auto-extracted graph shows the interrupt node as an `action_node` (auto-extraction doesn't know about human semantics -- it just sees nodes). This highlights a gap: auto-extraction can't distinguish human\_node from action\_node.
- **package.json:** includes `@langchain/langgraph`

### 5. `GRAPH_CONDITIONAL` -- Conditional branching

**Purpose:** Tests auto-extraction of `addConditionalEdges()` which produces edges with `conditional: true` and `data` labels.

- **Location:** `workflows/test/graph_conditional/`
- **manifest.yaml:** `name: GRAPH_CONDITIONAL`, no `graph:` section
- **Logic:** LangGraph with conditional routing: `classify_input` -> conditional edge -> either `handle_greeting` or `handle_question` -> `format_response`. Uses `addConditionalEdges('classify_input', routingFn, { greeting: 'handle_greeting', question: 'handle_question' })`.
- **Expected result:** Auto-extracted graph includes conditional edges with labels
- **package.json:** includes `@langchain/langgraph`

## Build and Deploy Sequence

For each workflow:

```
cd workflows/test/<name>
bun install                    # install dependencies (needed for LangGraph extraction)
p67 build                      # builds to build/, extracts graph.json if applicable
p67 workflow deploy             # uploads build/workflow.zip to SPCS controld
```

After deployment, verify:

- `GET /api/workflow/<id>/graph` returns expected graph (or null for GRAPH\_NONE)
- Dashboard shows graph tab for workflows with graphs

## Edge Cases Being Tested

| Workflow             | LangGraph? | Manual graph? | Expected graph source | Key test                      |
| -------------------- | ---------- | ------------- | --------------------- | ----------------------------- |
| GRAPH\_AUTO\_EXTRACT | Yes        | No            | `graph.json` (auto)   | Happy path auto-extraction    |
| GRAPH\_MANUAL        | No         | Yes           | `manifest.yaml`       | Manual graph takes precedence |
| GRAPH\_NONE          | No         | No            | null                  | Graceful empty state          |
| GRAPH\_HITL          | Yes        | No            | `graph.json` (auto)   | Interrupt node in graph       |
| GRAPH\_CONDITIONAL   | Yes        | No            | `graph.json` (auto)   | Conditional edges with labels |

## Files to Create (per workflow)

17 new files total:

- 5x `p67.yml`
- 5x `manifest.yaml`
- 5x `src/index.ts`
- 1x `src/sdk.ts` (shared, symlinked or copied to each)
- 1x `package.json` template (2 variants: with/without langgraph)
