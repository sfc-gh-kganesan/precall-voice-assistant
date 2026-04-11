# Agent Handoff: WASM Sandbox Experiments

> Last updated: March 5, 2026
> Status: Research complete — Docker recommended over WASM for P67

## What This Is

Evaluated WASM-based sandboxing (Pyodide + Wazero) as an alternative to Docker for P67 workflow execution.

**Conclusion**: WASM works but Docker is better for P67's LangGraph requirements.

## Why Docker Won

| Factor | WASM (Pyodide) | Docker |
|--------|----------------|--------|
| LangGraph support | ⚠️ Limited (version constraints) | ✅ Full |
| Cold start | ~890ms | ~95ms |
| Warm start | ~0.05ms | ~46ms |
| Python ecosystem | Limited (no native extensions) | Full |
| Complexity | High (Go→Node→Pyodide bridge) | Low |

## What We Learned

### LangGraph in Pyodide: Possible but Fragile
- Pyodide 0.29.3 works with `langgraph==0.0.38`
- Newer LangGraph versions fail due to pydantic/uuid-utils native dependencies
- Manual state machine fallback works if LangGraph breaks

### Architecture Required
```
Go Control Plane
  └── Node.js subprocess (IPC)
        └── Pyodide (CPython in WASM)
              └── LangGraph workflow
                    └── Host function calls → Go
```

This is complex. Docker pooling is simpler and faster.

## Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Pyodide in Node.js | ✅ Done | Works with constraints |
| Phase 2: Go + Wazero | ✅ Done | Bridge architecture works |
| Production use | ❌ Not recommended | Use Docker instead |

## How to Run

```bash
# Phase 1: Pyodide tests
cd phase1-pyodide-node
npm install
npm run test:all      # Run all tests

# Individual tests
npm run test:basic    # Basic Python execution
npm run test:langgraph # LangGraph import (may fail on version)
npm run test:workflow # Manual state machine
npm run test:host     # Host function calls

# Phase 2: Go bridge
cd phase2-go-wazero
npm install
node test_architecture.mjs  # Test Go→Node→Pyodide bridge
```

## Important Files

| File | Purpose |
|------|---------|
| `README.md` | Full research documentation with all alternatives |
| `phase1-pyodide-node/runner.js` | PyodideRunner + PyodidePool classes |
| `phase1-pyodide-node/tests/*.js` | Test suite |
| `phase2-go-wazero/main.go` | Go orchestration with host functions |
| `phase2-go-wazero/bridge.mjs` | Node.js IPC bridge |

## Key Metrics

```
Pyodide Performance:
- Cold start:        ~890ms
- Warm start:        ~0.05ms (from PyodidePool)
- Host call overhead: 0.09ms per call
- 100 host calls:    9ms total
```

## Version Constraints (Critical)

If you need to use Pyodide with LangGraph:
```
pyodide: 0.29.3
langgraph: 0.0.38  # Older version, but works
pydantic: 2.12.5   # Bundled with Pyodide 0.29.3
```

Newer versions fail due to:
- `pydantic-core` requiring native compilation
- `uuid-utils` requiring native compilation

## When to Use WASM Instead

WASM might be preferred if:
1. You need sub-millisecond warm starts
2. You're not using LangGraph (plain Python only)
3. You're in an environment where Docker is unavailable
4. You need V8-level memory isolation

## What's NOT in Scope

These were evaluated but rejected:
- **V8 Isolates**: JavaScript only, can't run Python
- **Javy**: Compiles to QuickJS (10-100x slower than V8 JIT)
- **CPython-WASI**: No pip, can't install LangGraph
