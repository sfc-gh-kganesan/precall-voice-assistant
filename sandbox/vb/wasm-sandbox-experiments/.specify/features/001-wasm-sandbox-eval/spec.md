# Specification: WASM Sandbox Evaluation for P67 Workflows

## Problem Statement
P67 currently executes user workflows in isolated processes (Node.js fork for TypeScript, Python spawn for Python). Docker containers are used in SPCS for production isolation. We want to evaluate if WebAssembly can provide:
- Faster startup times than containers
- Lower memory overhead
- Equivalent or better security isolation
- Support for both Python and TypeScript workflows

## User Stories

### US-1: Pyodide LangGraph Validation
**As a** P67 platform engineer  
**I want to** validate that LangGraph workflows can run inside Pyodide  
**So that** we know if WASM-based Python execution is viable for P67

**Acceptance Criteria:**
- [ ] Can import `langgraph` package in Pyodide
- [ ] Can create and run a simple StateGraph
- [ ] Can call mock SDK host functions from within the workflow
- [ ] Measure cold start time (target: <3s)
- [ ] Measure warm start time with instance pooling (target: <100ms)

### US-2: Go + Wazero Host
**As a** P67 platform engineer  
**I want to** run Pyodide from Go using Wazero  
**So that** we can integrate WASM sandboxing with a potential Go-based control plane

**Acceptance Criteria:**
- [ ] Load Pyodide WASM module in Wazero
- [ ] Execute Python code through Pyodide
- [ ] Implement SDK host functions callable from Python
- [ ] Demonstrate instance pooling for warm starts
- [ ] Measure memory per instance (target: <100MB)

### US-3: TypeScript via Javy
**As a** P67 platform engineer  
**I want to** compile TypeScript workflows to WASM using Javy  
**So that** TS workflows can also run in the WASM sandbox

**Acceptance Criteria:**
- [ ] Compile a simple TS workflow to WASM
- [ ] Execute the WASM module in Wazero
- [ ] SDK calls work via host functions
- [ ] Compare cold/warm start times vs Pyodide

### US-4: Performance Benchmarks
**As a** P67 decision maker  
**I want to** see quantified performance comparisons  
**So that** we can make an informed decision about WASM adoption

**Acceptance Criteria:**
- [ ] Benchmark: Cold start latency (WASM vs Docker vs current process model)
- [ ] Benchmark: Warm start latency with pooling
- [ ] Benchmark: Memory per execution instance
- [ ] Benchmark: Throughput (executions/second)
- [ ] Summary report with recommendations

## Non-Functional Requirements

### NFR-1: Security
- WASM execution must prevent access to host filesystem
- Network access only through explicit host functions
- No arbitrary code execution outside the sandbox

### NFR-2: Compatibility
- Must work with Python 3.11+ code patterns
- Must support async/await in workflows
- Must support LangGraph StateGraph patterns

### NFR-3: Observability
- Execution time must be measurable
- Memory usage must be trackable
- Errors must propagate clearly to the host

## Technical Constraints

### TC-1: Pyodide Limitations (known)
- Cold start is ~2-3 seconds (CPython initialization in WASM)
- Some Python packages won't work (native extensions not compiled for WASM)
- asyncio works but has limitations in non-browser environments

### TC-2: Wazero Limitations
- WASI Preview 1 only (no sockets, limited threading)
- Pyodide is Emscripten-based, may not be directly compatible
- May need Pyodide's "standalone" build

### TC-3: Javy Limitations
- Compiles to QuickJS, not full V8
- Node.js APIs not available
- Smaller ecosystem than native Node.js

## Open Questions

1. **Can Pyodide run in Wazero?** - Pyodide is built for Emscripten, Wazero is WASI
2. **How to handle async in Go host?** - Pyodide async bridges to JS event loop
3. **Package installation?** - Can micropip work without network access?
4. **State serialization?** - How to checkpoint/restore workflow state?

## Success Metrics

| Metric | Target | Acceptable | Failure |
|--------|--------|------------|---------|
| Cold start | <2s | <5s | >10s |
| Warm start | <100ms | <500ms | >1s |
| Memory/instance | <100MB | <200MB | >500MB |
| LangGraph compat | Full | Partial | None |
