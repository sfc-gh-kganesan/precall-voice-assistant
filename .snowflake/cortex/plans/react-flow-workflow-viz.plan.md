---
name: "react flow workflow viz"
created: "2026-03-12T17:01:26.684Z"
status: pending
---

# Plan: React Flow Workflow Visualization

## Architecture Overview

```
flowchart TD
    subgraph sources [Graph Topology Sources]
        LG[LangGraph Auto-Extract]
        MF[Manifest Declaration]
    end
    subgraph backend [Backend - controld]
        WS[WorkflowService.create]
        DB[(Postgres - WorkflowGraph table)]
        API["/api/workflow/:id/graph"]
        RunAPI["/api/workflow/runs/:id"]
    end
    subgraph frontend [Frontend - tools/dash]
        RF[React Flow Component]
        CN[Custom Node Components]
        EO[Execution Overlay]
        HITL[Inline Interrupt Controls]
    end
    LG -->|"compile() hook"| WS
    MF -->|"manifest.yaml graph:"| WS
    WS --> DB
    DB --> API
    API --> RF
    RunAPI -->|"logs + interrupts"| EO
    RF --> CN
    RF --> EO
    EO --> HITL
```

## Data Flow

```
sequenceDiagram
    participant Author as Workflow Author
    participant SDK as P67 SDK / Deploy
    participant API as controld API
    participant DB as Postgres
    participant Dash as Dashboard
    participant RF as React Flow

    Note over Author,RF: Registration Time
    Author->>SDK: Deploy workflow (ZIP)
    SDK->>SDK: Parse manifest.yaml
    alt LangGraph workflow
        SDK->>SDK: Import module, call getGraph()
        SDK->>SDK: Extract nodes + edges from LangGraph
    else Manual graph in manifest
        SDK->>SDK: Read graph: section
    end
    SDK->>DB: Store WorkflowGraph JSON

    Note over Author,RF: Execution Time
    Dash->>API: GET /workflow/:id/graph
    API->>DB: Fetch graph topology
    API-->>Dash: { nodes, edges }
    Dash->>RF: Render graph with dagre layout
    Dash->>API: GET /workflow/runs/:runId (poll 5s)
    API-->>Dash: { status, logs, interrupts }
    Dash->>RF: Overlay execution state on nodes
    RF->>RF: Animate node transitions
    alt Interrupt on human_node
        RF->>RF: Show approve/reject on node
        RF->>API: POST /workflow/interrupts/:id/resume
    end
```

---

## Task 1: Graph Data Model and API

### 1a. Prisma Schema - Add WorkflowGraph

Add to packages/db/prisma/schema.prisma:

```
model WorkflowGraph {
    id          String   @id @default(uuid())
    workflowId  String   @unique
    workflow    Workflow  @relation(fields: [workflowId], references: [id], onDelete: Cascade)
    source      String   // "langgraph" | "manifest" 
    graph       Json     // { nodes: GraphNode[], edges: GraphEdge[] }
    createdAt   DateTime @default(now())
    updatedAt   DateTime @updatedAt
}
```

Graph JSON shape (aligned with existing workflow\_graph\_schema.json):

```
interface WorkflowGraphData {
    nodes: {
        id: string;
        type: "start_node" | "action_node" | "decision_node" | "human_node" | "subgraph_node" | "query_node" | "end_node";
        name: string;
        description?: string;
    }[];
    edges: {
        id: string;
        from_node: string;
        to_node: string;
        label?: string;
    }[];
}
```

### 1b. API Endpoint

New route at services/controld/src/routes/workflow/graph.ts:

- `GET /api/workflow/:workflowId/graph` - Returns the graph topology JSON (or 404 if no graph available)

### 1c. Execution State Mapping

No new endpoint needed. The existing `GET /api/workflow/runs/:runId` already returns logs (with `source` field) and interrupts (with `nodeId` field). The frontend will map:

- Log events with `source: "WorkflowNode"` and attributes containing node identifiers to active/completed nodes
- `WorkflowInterrupt` records with `nodeId` to interrupted nodes
- Run `status` to overall graph state

**Key insight**: The SDK's `interrupt()` already accepts `nodeId` in `InterruptOptions`. We need to ensure LangGraph workflows pass the correct nodeId, and that log messages from nodes include identifiers we can map.

---

## Task 2: LangGraph Auto-Extraction

### Problem

The P67 SDK currently treats workflows as opaque scripts. For LangGraph workflows (like example\_workflows/number\_one/src/index.ts), we need to extract the graph topology at deploy time.

### Approach

Add a **post-registration extraction step** in the workflow creation flow. After the ZIP is extracted and manifest parsed:

1. Check if the workflow uses LangGraph (detect `@langchain/langgraph` in package.json or `langgraph` in requirements.txt)
2. If yes, run a lightweight extraction script that imports the module and calls LangGraph's `.get_graph()` method
3. Store the extracted topology as a `WorkflowGraph` record

### Implementation

In services/controld/src/routes/workflow/create.ts, after `workflowService.create()`:

```
// After workflow is created and files extracted to disk
const graphData = await extractGraphTopology(storagePath, manifest);
if (graphData) {
    await db.workflowGraph.upsert({
        where: { workflowId },
        create: { workflowId, source: graphData.source, graph: graphData.graph },
        update: { source: graphData.source, graph: graphData.graph },
    });
}
```

New file `services/controld/src/lib/graph-extractor.ts`:

- `extractGraphTopology(storagePath, manifest)` - orchestrates extraction

- `extractFromManifest(manifest)` - reads `graph:` section if present

- `extractFromLangGraph(storagePath, language)` - runs extraction script

  - For TypeScript: spawns `node -e "import(...).then(m => m.getGraph())"` against the compiled workflow
  - For Python: spawns `python -c "from main import ...; print(graph.get_graph().to_json())"`
  - Falls back gracefully if extraction fails (graph is optional)

### LangGraph `.get_graph()` Output

LangGraph's `CompiledGraph.get_graph()` returns a `Graph` object with:

- `nodes`: `{ id: string, name: string, data: { type: string } }[]`
- `edges`: `{ source: string, target: string, data?: { condition?: string } }[]`

We transform this to our schema format, mapping LangGraph node types to our node types:

- `__start__` -> `start_node`
- `__end__` -> `end_node`
- Nodes with `interrupt_before` or `interrupt_after` -> `human_node`
- All others -> `action_node`

---

## Task 3: Manifest Graph Declaration

Extend services/controld/src/lib/manifest.ts `ManifestSchema` with an optional `graph` field:

```
# manifest.yaml example
name: data-pipeline
visibility: public
params:
  customer:
    required: true
    description: Customer name

graph:
  nodes:
    - id: start
      type: start_node
      name: Start
    - id: fetch_data
      type: action_node
      name: Fetch Data
      description: Pull data from warehouse
    - id: review
      type: human_node
      name: Human Review
      description: Approve data quality
    - id: transform
      type: action_node
      name: Transform
    - id: done
      type: end_node
      name: Complete
  edges:
    - from_node: start
      to_node: fetch_data
    - from_node: fetch_data
      to_node: review
    - from_node: review
      to_node: transform
      label: Approved
    - from_node: transform
      to_node: done
```

Resolution order in `extractGraphTopology()`:

1. `manifest.graph` (explicit declaration takes precedence)
2. LangGraph auto-extraction (if LangGraph detected)
3. No graph (return null - dashboard shows timeline-only view)

---

## Task 4: React Flow Graph Component

### Install Dependencies

In tools/dash/package.json:

```
@xyflow/react (React Flow v12)
dagre (auto-layout)
@dagrejs/dagre (types)
```

### Component Structure

```
tools/dash/src/components/workflow-graph/
  WorkflowGraph.tsx          -- Main React Flow wrapper
  nodes/
    ActionNode.tsx           -- Default step node
    DecisionNode.tsx         -- Diamond-shaped branching node
    HumanNode.tsx            -- HITL interrupt node (with inline controls)
    StartNode.tsx            -- Entry point (circle)
    EndNode.tsx              -- Terminal (double circle)
    SubgraphNode.tsx         -- Nested workflow reference
  edges/
    AnimatedEdge.tsx         -- Edge with flowing dot animation
  layout.ts                  -- Dagre auto-layout utility
  execution-overlay.ts       -- Maps run state to node/edge styles
  types.ts                   -- Shared types
```

### Custom Node Design

Each node type gets a distinct visual treatment following Stellar design patterns:

| Node Type       | Shape                    | Visual                                           |
| --------------- | ------------------------ | ------------------------------------------------ |
| `start_node`    | Rounded pill             | Gray, minimal                                    |
| `action_node`   | Rounded rectangle        | White card with title + description              |
| `decision_node` | Diamond                  | Amber accent, shows branch conditions on edges   |
| `human_node`    | Rectangle with user icon | Blue accent, shows interrupt payload when active |
| `query_node`    | Rectangle with DB icon   | Purple accent                                    |
| `end_node`      | Rounded pill             | Green (success) / Red (failure)                  |
| `subgraph_node` | Dashed rectangle         | Expandable to show sub-graph                     |

### Auto-Layout with Dagre

```
// layout.ts
import dagre from 'dagre';

export function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]): { nodes: Node[], edges: Edge[] } {
    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 50 });
    g.setDefaultEdgeLabel(() => ({}));
    
    nodes.forEach(n => g.setNode(n.id, { width: 220, height: 80 }));
    edges.forEach(e => g.setEdge(e.from_node, e.to_node));
    dagre.layout(g);
    
    // Map back to React Flow nodes with computed positions
    return { nodes: ..., edges: ... };
}
```

---

## Task 5: Live Execution Overlay

### Node State Machine

```
stateDiagram-v2
    [*] --> Idle
    Idle --> Running: log event matches node
    Running --> Completed: next node starts / success log
    Running --> Failed: error log
    Running --> Interrupted: interrupt created
    Interrupted --> Running: interrupt resumed
    Completed --> [*]
    Failed --> [*]
```

### Mapping Strategy

The execution overlay watches the run's logs and interrupts (polled every 5s via existing `useLogs` and `useRunStatus` hooks) and maps them to node states:

1. **Log-based mapping**: Logs with `source: "WorkflowNode"` that contain a node identifier in their `attributes` or `message` (e.g., `"Executing node: fetch_data"`) trigger `Running` state on that node.

2. **Interrupt-based mapping**: `WorkflowInterrupt` records with `nodeId` set trigger `Interrupted` state. When `status` changes to `Resumed`, the node returns to `Running`.

3. **Sequential inference**: If no explicit node identifiers exist in logs, we can infer which node is active based on the graph topology and log ordering (first node after start, etc.).

### Visual Treatment

| State       | Node Style                          | Edge Style            |
| ----------- | ----------------------------------- | --------------------- |
| Idle        | Muted, gray border                  | Gray, no animation    |
| Running     | Pulsing blue glow, bold border      | Animated flowing dots |
| Completed   | Green checkmark badge, solid border | Green, no animation   |
| Failed      | Red X badge, red border             | Red                   |
| Interrupted | Amber pause icon, amber border      | Amber, pulsing        |

### Animation

- **Edge flow animation**: CSS `stroke-dasharray` + `stroke-dashoffset` animation on the active edge(s) - a classic "marching ants" effect showing data flowing between nodes
- **Node pulse**: CSS `box-shadow` animation with `@keyframes` for the running state glow
- **Transition**: Smooth 300ms color transitions between states using CSS transitions
- **Entry**: Nodes fade in with a slight scale-up when first rendered

---

## Task 6: Inline HITL Interrupt Controls

When a `human_node` enters the `Interrupted` state, the node component expands to show:

```
+----------------------------------+
|  [Pause Icon]  Human Review      |
|                                  |
|  "Review data quality results"   |
|                                  |
|  Payload:                        |
|  { metrics: { accuracy: 0.95 } } |
|                                  |
|  [Approve]  [Reject]  [Custom]   |
+----------------------------------+
```

- **Approve/Reject** buttons call `POST /api/workflow/interrupts/:id/resume` with `{ response: "approved" }` or `{ response: "rejected" }`
- **Custom** opens a text input for freeform responses
- Uses existing `useResumeInterrupt` hook from the dashboard
- Node collapses back after resume, transitions to `Running`

---

## Task 7: Dashboard Integration

### WorkflowDetailPage - Design View

Add a "Graph" tab alongside the existing content on tools/dash/src/pages/WorkflowDetailPage.tsx:

```
+--------------------------------------------------+
|  Workflow: data-pipeline          [Public] [Run]  |
|  [Details]  [Graph]  [Runs]                       |
+--------------------------------------------------+
|                                                   |
|  [React Flow canvas - static graph]               |
|  Shows topology without execution state            |
|  Zoom, pan, fit-to-view controls                  |
|                                                   |
+--------------------------------------------------+
```

### RunDetailPage - Execution View

Split layout on tools/dash/src/pages/RunDetailPage.tsx:

```
+-------------------------+------------------------+
|                         |  Status: Running       |
|  [React Flow canvas]    |  Duration: 1m 23s      |
|  with execution overlay |                        |
|  - nodes light up       |  [Logs]                |
|  - edges animate        |  > Fetching data...    |
|  - HITL inline          |  > Processing 1000 rows|
|                         |  > Waiting for review  |
|  [Fit] [Zoom] [Toggle]  |  [Interrupts]          |
|                         |  > Review pending      |
+-------------------------+------------------------+
```

If no graph is available for the workflow, the run detail page falls back to the current full-width log view (no graph panel).

### New Hook

```
// tools/dash/src/hooks/useWorkflowGraph.ts
export function useWorkflowGraph(workflowId: string) {
    return useQuery({
        queryKey: ['workflow-graph', workflowId],
        queryFn: () => api.workflow.getGraph(workflowId),
        staleTime: Infinity, // graph topology doesn't change during a run
    });
}
```

---

## Task 8: Testing and Polish

1. **Create a test LangGraph workflow** with multiple node types (action, decision, human) and conditional edges to exercise the full visualization
2. **Deploy via CLI** and verify auto-extraction populates the graph
3. **Test manifest-declared graph** with a non-LangGraph workflow
4. **Run workflow from Slack** (`/p67-workflow run`) and verify live graph updates on the dashboard
5. **Test HITL flow**: trigger interrupt, verify node shows controls, approve from graph, verify workflow continues
6. **Edge cases**: workflow with no graph (fallback), very large graphs (performance), concurrent runs
7. **Polish**: ensure animations are smooth, colors match Stellar palette, responsive layout works

---

## Files Modified/Created Summary

| File                                              | Action | Purpose                            |
| ------------------------------------------------- | ------ | ---------------------------------- |
| `packages/db/prisma/schema.prisma`                | Modify | Add WorkflowGraph model            |
| `packages/db/prisma/migrations/...`               | Create | Migration for WorkflowGraph        |
| `services/controld/src/lib/manifest.ts`           | Modify | Add graph to ManifestSchema        |
| `services/controld/src/lib/graph-extractor.ts`    | Create | Graph extraction logic             |
| `services/controld/src/routes/workflow/graph.ts`  | Create | GET graph API endpoint             |
| `services/controld/src/routes/workflow/index.ts`  | Modify | Register graph route               |
| `services/controld/src/routes/workflow/create.ts` | Modify | Call graph extraction after create |
| `tools/dash/package.json`                         | Modify | Add @xyflow/react, dagre           |
| `tools/dash/src/components/workflow-graph/`       | Create | All graph visualization components |
| `tools/dash/src/hooks/useWorkflowGraph.ts`        | Create | Graph data hook                    |
| `tools/dash/src/pages/WorkflowDetailPage.tsx`     | Modify | Add Graph tab                      |
| `tools/dash/src/pages/RunDetailPage.tsx`          | Modify | Add split layout with graph panel  |
