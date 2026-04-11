# Tasks: WASM Sandbox Evaluation

## Phase 1: Pyodide + Node.js Validation

### Task 1.1: Setup Node.js project
- [x] Create `phase1-pyodide-node/` directory structure
- [x] Initialize `package.json` with Pyodide dependency
- [x] Verify Node.js can load Pyodide

### Task 1.2: Basic Pyodide execution
- [x] Create `runner.js` - Pyodide initialization and code execution
- [x] Create `tests/basic_python.js` - Simple Python code execution
- [x] Measure cold start time → **~890ms**
- [ ] Measure memory usage

### Task 1.3: LangGraph import test
- [x] Create `tests/langgraph_import.js`
- [x] Test: `import langgraph` works → **FAILED** (pydantic version conflict)
- [x] Test: `import langchain_core` works → **FAILED** (requires pydantic>=2.7.4)
- [x] Document import failures → **Pyodide bundles pydantic 2.7.0, langchain-core requires >=2.7.4**

### Task 1.4: StateGraph workflow test
- [x] Create `workflows/sample_workflow.py` - P67-style workflow
- [x] Create `tests/stateful_workflow.js` - Execute the workflow
- [x] Verify state transitions work → **PASS (manual state machine fallback)**
- [x] Test async node execution → **PASS**

### Task 1.5: Host function simulation
- [x] Create `tests/host_functions.js`
- [x] Implement mock `execute_query` host function → **PASS**
- [x] Implement mock `cortex_complete` host function → **PASS**
- [x] Test calling host functions from Python workflow → **PASS**
- [x] Measure host function call overhead → **0.09ms per call**

### Task 1.6: Instance pooling test
- [x] Implement warm instance reuse in `runner.js` → **PyodidePool class**
- [x] Measure warm start time → **0.05ms (target: <100ms)** ✓
- [x] Document pooling strategy

### Phase 1 Results Summary
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Cold start | 890ms | <3000ms | ✓ |
| Warm start | 0.05ms | <100ms | ✓ |
| Host call overhead | 0.09ms | <10ms | ✓ |
| LangGraph import | FAIL | PASS | ✗ |

**Key Blocker**: LangGraph cannot run in Pyodide due to pydantic version conflict.
**Workaround**: Manual state machine works; workflows can run without LangGraph.

---

## Phase 2: Go + Wazero Integration

### Task 2.1: Wazero project setup
- [ ] Create `phase2-go-wazero/` directory
- [ ] Initialize Go module with Wazero dependency
- [ ] Create basic Wazero hello-world test

### Task 2.2: Pyodide WASM compatibility check
- [ ] Download Pyodide standalone WASM build
- [ ] Attempt to load in Wazero
- [ ] Document compatibility issues (Emscripten vs WASI)
- [ ] If incompatible, document alternative approaches

### Task 2.3: Host function implementation (if compatible)
- [ ] Create `runtime/host_functions.go`
- [ ] Implement `_p67_call` host function
- [ ] Implement JSON protocol marshaling
- [ ] Test from Go

### Task 2.4: Instance pooling in Go
- [ ] Create `runtime/pool.go`
- [ ] Implement pre-initialized instance pool
- [ ] Benchmark warm start from pool
- [ ] Document memory per pooled instance

### Task 2.5: Integration test
- [ ] Create `tests/pyodide_test.go`
- [ ] Execute sample Python workflow
- [ ] Verify results match Node.js execution

---

## Phase 3: TypeScript via Javy

### Task 3.1: Javy toolchain setup
- [ ] Verify Javy CLI is installed
- [ ] Create `phase3-javy-ts/` directory
- [ ] Create build script `build.sh`

### Task 3.2: TypeScript workflow compilation
- [ ] Create `src/workflow.ts` - Minimal workflow
- [ ] Create `src/sdk_shim.ts` - SDK→host function bridge
- [ ] Compile TS → JS via esbuild
- [ ] Compile JS → WASM via Javy

### Task 3.3: Wazero execution
- [ ] Create `go/runner.go` - Wazero runner for Javy WASM
- [ ] Load and execute compiled WASM
- [ ] Implement host functions for SDK calls

### Task 3.4: Comparison test
- [ ] Execute same workflow logic as Phase 1/2
- [ ] Measure cold/warm start times
- [ ] Compare with Pyodide results

---

## Phase 4: Benchmarks

### Task 4.1: Benchmark framework
- [ ] Create `phase4-benchmarks/benchmark.sh`
- [ ] Define benchmark scenarios
- [ ] Setup results collection

### Task 4.2: Cold start benchmarks
- [x] Benchmark: Pyodide (Node.js) cold start → **890ms**
- [ ] Benchmark: Pyodide (Wazero) cold start (if compatible)
- [ ] Benchmark: Javy cold start
- [ ] Benchmark: Docker container cold start (baseline)
- [ ] Benchmark: Node.js process fork (current P67)

### Task 4.3: Warm start benchmarks
- [x] Benchmark: Pyodide pooled instance → **0.05ms**
- [ ] Benchmark: Javy pooled instance
- [ ] Benchmark: Docker with kept-alive container

### Task 4.4: Memory benchmarks
- [ ] Measure: Memory per Pyodide instance
- [ ] Measure: Memory per Javy instance
- [ ] Measure: Memory per Docker container

### Task 4.5: Throughput benchmarks
- [ ] Measure: Executions/second (Pyodide pool)
- [ ] Measure: Executions/second (Javy pool)
- [ ] Measure: Executions/second (Docker)

### Task 4.6: Final report
- [ ] Create `report.md` with all results
- [ ] Include recommendation matrix
- [ ] Document trade-offs and blockers
- [ ] Provide go/no-go recommendation

---

## Definition of Done

Each phase is complete when:
1. All tasks marked complete
2. Tests pass
3. Benchmarks recorded
4. Documentation updated
5. Blockers documented
