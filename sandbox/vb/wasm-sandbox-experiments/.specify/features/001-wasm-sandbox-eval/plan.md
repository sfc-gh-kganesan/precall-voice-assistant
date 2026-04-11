# Implementation Plan: WASM Sandbox Evaluation

## Technology Choices

### Phase 1: Pyodide + Deno (Validation)
- **Runtime**: Deno (like langchain-sandbox)
- **Why Deno**: Proven to work with Pyodide, TypeScript native, good sandbox permissions
- **Fallback**: Node.js with Pyodide standalone

### Phase 2: Go + Wazero (Integration)
- **Runtime**: Wazero (pure Go WASM runtime)
- **Why Wazero**: No CGO, good WASI support, production-proven (Arcjet)
- **Challenge**: Pyodide compatibility with WASI vs Emscripten

### Phase 3: TypeScript via Javy (Alternative)
- **Compiler**: Javy (Bytecode Alliance)
- **Runtime**: Wazero
- **Why Javy**: Mature JS→WASM compiler, designed for server-side

### Phase 4: Benchmarking
- **Tools**: hyperfine (CLI), custom Go benchmarks
- **Comparison**: WASM vs Docker vs Node.js process fork

## Architecture

```
experiments/wasm/
├── .specify/                    # Spec-kit artifacts
│   ├── memory/constitution.md
│   └── features/001-wasm-sandbox-eval/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
├── README.md                    # Overview and research summary
├── phase1-pyodide-deno/         # Deno-based Pyodide validation
│   ├── deno.json
│   ├── runner.ts                # Deno Pyodide executor
│   ├── tests/
│   │   ├── basic_python.ts      # Basic Pyodide execution
│   │   ├── langgraph_import.ts  # LangGraph import test
│   │   ├── stateful_workflow.ts # StateGraph execution
│   │   └── host_functions.ts    # SDK host function simulation
│   └── workflows/
│       └── sample_workflow.py   # Test workflow
├── phase2-go-wazero/            # Go + Wazero integration
│   ├── go.mod
│   ├── main.go                  # Entry point
│   ├── runtime/
│   │   ├── pyodide.go           # Pyodide WASM loader
│   │   ├── host_functions.go    # SDK host function impl
│   │   └── pool.go              # Instance pooling
│   ├── tests/
│   │   └── pyodide_test.go
│   └── workflows/
│       └── sample_workflow.py
├── phase3-javy-ts/              # TypeScript via Javy
│   ├── build.sh                 # TS → WASM pipeline
│   ├── src/
│   │   ├── workflow.ts          # Sample TS workflow
│   │   └── sdk_shim.ts          # SDK→host function bridge
│   ├── go/
│   │   └── runner.go            # Wazero runner for Javy WASM
│   └── tests/
│       └── javy_test.go
└── phase4-benchmarks/           # Performance comparison
    ├── benchmark.sh
    ├── results/
    │   └── .gitkeep
    └── report.md
```

## SDK Host Function Protocol

All SDK operations will be implemented as WASM host functions using a simple JSON protocol:

```
┌─────────────────────────────────────────────────────────────┐
│                    WASM Guest (Workflow)                    │
│  sdk.execute_query("SELECT * FROM t")                       │
│           │                                                 │
│           ▼                                                 │
│  _p67_call(JSON.stringify({                                 │
│      method: "execute_query",                               │
│      params: { sql: "SELECT * FROM t" }                     │
│  }))                                                        │
└─────────────────────────────────────────────────────────────┘
           │
           ▼ (linear memory pointer + length)
┌─────────────────────────────────────────────────────────────┐
│                    WASM Host (Go/Deno)                      │
│  1. Read JSON from guest memory                             │
│  2. Dispatch to handler (mock for experiment)               │
│  3. Write response JSON to guest memory                     │
│  4. Return pointer + length                                 │
└─────────────────────────────────────────────────────────────┘
```

## Dependencies

### Phase 1 (Deno)
```json
{
  "imports": {
    "pyodide": "npm:pyodide@0.26.0"
  }
}
```

### Phase 2 (Go)
```go
require (
    github.com/tetratelabs/wazero v1.7.0
)
```

### Phase 3 (Javy)
```bash
cargo install javy-cli
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Pyodide doesn't work in Wazero | Use Deno as fallback host, document incompatibility |
| LangGraph has native deps | Test with minimal LangGraph (no optional features) |
| Cold start too slow | Focus on warm start pooling strategy |
| Host function overhead high | Batch operations, minimize round-trips |

## Milestones

1. **M1: Pyodide validates** - LangGraph runs in Pyodide + Deno
2. **M2: Wazero spike** - Determine if Pyodide WASM works in Wazero
3. **M3: Host functions** - SDK mock operations work across WASM boundary
4. **M4: Benchmarks** - Quantified comparison with current approach
5. **M5: Report** - Final recommendation document
