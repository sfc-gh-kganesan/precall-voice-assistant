---
name: "python graph extraction"
created: "2026-03-18T00:16:38.188Z"
status: pending
---

# Plan: Python LangGraph Graph Extraction + Test Workflows

## Context

Currently, LangGraph graph extraction only works for TypeScript workflows (`build.ts:210-212`). The Python `langgraph` package has an identical API (`StateGraph.compile()` -> `.get_graph()` -> nodes/edges), so the same technique applies. We need:

1. Python test workflows to establish what the source looks like
2. A Python extraction function in `build.ts`
3. E2E deployment verification

## Architecture

The extraction technique is the same as TypeScript -- monkey-patch `StateGraph.compile` to capture compiled graphs, import the entrypoint, call `.get_graph()` on the last captured graph, serialize nodes/edges to `graph.json`:

```
flowchart LR
    A[p67 build] --> B{language?}
    B -->|typescript| C[extractLangGraph via bun]
    B -->|python| D[extractLangGraphPython via venv]
    C --> E[graph.json in buildDir]
    D --> E
    E --> F[zip scan picks it up]
    F --> G[workflow.zip]
```

## Task 1: Create `py_graph_auto_extract` test workflow

**Location**: `p67/workflows/test/py_graph_auto_extract/`

**Structure**:

```
py_graph_auto_extract/
  p67.yml              # buildDir: build
  manifest.yaml        # name: PY_GRAPH_AUTO_EXTRACT, params: input
  requirements.txt     # langgraph>=0.2.0
  src/
    main.py            # StateGraph with 3 nodes: validate -> process -> format
```

**`src/main.py`** -- direct port of the TS `graph_auto_extract/src/index.ts`:

```
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class State(TypedDict):
    input: str
    validated: bool
    processed: str
    result: dict | None

def validate_input(state: State) -> dict:
    valid = isinstance(state["input"], str) and len(state["input"].strip()) > 0
    print(f'[validate_input] input="{state["input"]}" valid={valid}')
    return {"validated": valid}

def process_data(state: State) -> dict:
    if not state["validated"]:
        return {"processed": ""}
    processed = state["input"].strip().upper()[::-1]
    print(f'[process_data] "{state["input"]}" -> "{processed}"')
    return {"processed": processed}

def format_output(state: State) -> dict:
    from datetime import datetime, timezone
    return {"result": {
        "original": state["input"],
        "processed": state["processed"],
        "valid": state["validated"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }}

workflow = StateGraph(State)
workflow.add_node("validate_input", validate_input)
workflow.add_node("process_data", process_data)
workflow.add_node("format_output", format_output)
workflow.add_edge(START, "validate_input")
workflow.add_edge("validate_input", "process_data")
workflow.add_edge("process_data", "format_output")
workflow.add_edge("format_output", END)

app = workflow.compile()

def main(sdk):
    inp = sdk.get_parameter("input")
    result = app.invoke({"input": inp, "validated": False, "processed": "", "result": None})
    return result["result"]
```

Key differences from TS version:

- Python uses `TypedDict` instead of `Annotation.Root`
- `START`/`END` constants instead of `__start__`/`__end__` strings
- `def main(sdk)` is synchronous (Python host.py calls it synchronously)
- No `sdk` in state (Python host handles SDK lifecycle externally)

## Task 2: Create `py_graph_conditional` test workflow

**Location**: `p67/workflows/test/py_graph_conditional/`

Port of `graph_conditional`. Uses `add_conditional_edges` for routing:

```
def route_by_category(state: State) -> str:
    match state["category"]:
        case "greeting": return "handle_greeting"
        case "question": return "handle_question"
        case _: return "handle_statement"

workflow.add_conditional_edges("classify_input", route_by_category, {
    "handle_greeting": "handle_greeting",
    "handle_question": "handle_question",
    "handle_statement": "handle_statement",
})
```

Expected graph: 7 nodes (start, classify\_input, handle\_greeting, handle\_question, handle\_statement, format\_response, end), 8 edges (including 3 conditional).

## Task 3: Create `py_graph_none` test workflow

**Location**: `p67/workflows/test/py_graph_none/`

Simple Python workflow with NO langgraph dependency. No `requirements.txt` (or one without langgraph). Validates that extraction is gracefully skipped.

```
def main(sdk):
    message = sdk.get_parameter("message")
    print(f'[echo] Received: "{message}"')
    return {
        "echo": message,
        "reversed": message[::-1],
        "length": len(message),
    }
```

## Task 4: Add `extractLangGraphPython` to `build.ts`

**File**: `p67/tools/p67-cli/src/commands/build.ts`

Add a new function after the existing `extractLangGraph` (line 106):

```
async function extractLangGraphPython(
    entrypoint: string,
    buildDir: string,
    projectDir: string,
): Promise<void> {
    // Check if langgraph is in requirements.txt -- skip if not
    const reqPath = path.join(projectDir, "requirements.txt");
    if (!fs.existsSync(reqPath)) return;
    const reqContent = fs.readFileSync(reqPath, "utf-8");
    if (!reqContent.match(/langgraph/i)) return;

    const outputPath = path.join(buildDir, "graph.json");
    const scriptPath = path.join(projectDir, "__extract_graph.py");

    const script = `
import sys, json, os
sys.path.insert(0, os.path.dirname("${entrypoint}"))

# ... monkey-patch, import, extract (see below)
`;

    fs.writeFileSync(scriptPath, script);
    const venvDir = path.join(projectDir, "__extract_venv");

    try {
        // Create venv + install requirements
        Bun.spawnSync(["python3", "-m", "venv", venvDir], { cwd: projectDir });
        const pip = path.join(venvDir, "bin", "pip");
        Bun.spawnSync([pip, "install", "-q", "-r", reqPath], {
            cwd: projectDir, stdout: "inherit", stderr: "inherit"
        });

        // Run extraction
        const python = path.join(venvDir, "bin", "python");
        const proc = Bun.spawn([python, scriptPath], {
            stdout: "inherit", stderr: "inherit", cwd: projectDir
        });
        await proc.exited;
    } finally {
        // Cleanup
        if (fs.existsSync(scriptPath)) fs.unlinkSync(scriptPath);
        if (fs.existsSync(venvDir)) fs.rmSync(venvDir, { recursive: true, force: true });
    }
}
```

**The Python extraction script** (embedded in `build.ts` as a template string):

```
import sys, json, os, importlib.util

entrypoint = "<ENTRYPOINT>"  # injected by build.ts
output_path = "<OUTPUT_PATH>"  # injected by build.ts

sys.path.insert(0, os.path.dirname(os.path.abspath(entrypoint)))

try:
    from langgraph.graph import StateGraph
except ImportError:
    print("No langgraph found, skipping")
    sys.exit(0)

captured = []
orig_compile = StateGraph.compile

def patched_compile(self, *args, **kwargs):
    c = orig_compile(self, *args, **kwargs)
    captured.append(c)
    return c

StateGraph.compile = patched_compile

try:
    spec = importlib.util.spec_from_file_location("workflow", entrypoint)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
except Exception as e:
    print(f"Graph extraction skipped: {e}")
    sys.exit(0)
finally:
    StateGraph.compile = orig_compile

if not captured:
    print("No LangGraph compile() detected, skipping")
    sys.exit(0)

graph = captured[-1].get_graph()

def map_id(id):
    if id == "__start__": return "start"
    if id == "__end__": return "end"
    return id

def map_type(id):
    if id in ("__start__", "start"): return "start_node"
    if id in ("__end__", "end"): return "end_node"
    return "action_node"

def map_name(id, node):
    if id == "__start__": return "Start"
    if id == "__end__": return "End"
    name = getattr(node, "name", id)
    if name and name != id: return name
    return id.replace("_", " ").replace("-", " ").title()

nodes = [{"id": map_id(id), "type": map_type(id), "name": map_name(id, node)}
         for id, node in graph.nodes.items()]

edges = []
for i, edge in enumerate(graph.edges, 1):
    e = {"id": f"e{i}", "from_node": map_id(edge.source), "to_node": map_id(edge.target)}
    if edge.data and edge.conditional:
        e["label"] = edge.data
    edges.append(e)

result = {"name": "Workflow", "description": "Auto-extracted from LangGraph", "nodes": nodes, "edges": edges}
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)
print(f"Extracted graph to {output_path} - nodes: {len(nodes)} edges: {len(edges)}")
```

**Integration point** -- modify `build.ts` line 210-213:

```
// Before (line 210-213):
if (language === "typescript") {
    await extractLangGraph(entrypoint, buildDir, projectDir);
}

// After:
if (language === "typescript") {
    await extractLangGraph(entrypoint, buildDir, projectDir);
} else if (language === "python") {
    await extractLangGraphPython(entrypoint, buildDir, projectDir);
}
```

### Why a temp venv?

The customer's system may not have `langgraph` installed globally. Since `requirements.txt` declares it, we create a throwaway venv, install deps, run the extraction script inside it, then delete everything. This is the same pattern as the TS approach (which relies on the project's `node_modules`). The venv adds \~10-20s but is fully self-contained.

## Task 5: Build all 3 workflows locally

```
cd p67/workflows/test/py_graph_auto_extract && p67 build
# Expected: build/ contains main.py, p67_sdk/, requirements.txt, manifest.yaml, graph.json, workflow.zip

cd p67/workflows/test/py_graph_conditional && p67 build
# Expected: same structure, graph.json with 7 nodes + 8 edges

cd p67/workflows/test/py_graph_none && p67 build
# Expected: NO graph.json (no langgraph in requirements.txt)
```

## Task 6: Deploy to AIFDE SPCS

```
cd p67/workflows/test/py_graph_auto_extract && p67 deploy --endpoint https://fkc46h6e-sfengineering-aifde.snowflakecomputing.app/
cd p67/workflows/test/py_graph_conditional && p67 deploy --endpoint ...
cd p67/workflows/test/py_graph_none && p67 deploy --endpoint ...
```

## Task 7: Verify via graph API

For each deployed workflow, hit the graph endpoint:

```
curl -H "Authorization: Bearer $PAT" https://fkc46h6e-sfengineering-aifde.snowflakecomputing.app/api/workflow/<ID>/graph
```

Expected:

| Workflow                 | Graph                            |
| ------------------------ | -------------------------------- |
| PY\_GRAPH\_AUTO\_EXTRACT | graph.json with 5 nodes, 4 edges |
| PY\_GRAPH\_CONDITIONAL   | graph.json with 7 nodes, 8 edges |
| PY\_GRAPH\_NONE          | `{ "graph": null }`              |
