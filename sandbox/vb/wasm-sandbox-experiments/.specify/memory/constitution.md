# P67 WASM Sandbox Experiment - Constitution

## Project Vision
Evaluate WebAssembly-based sandboxing as a lightweight, secure alternative to Docker containers for executing P67 workflows.

## Governing Principles

### 1. Experiment-First Mindset
- This is exploratory research, not production code
- Prioritize learning and validation over polish
- Document findings, limitations, and blockers clearly
- Fail fast and pivot when approaches don't work

### 2. Minimal Dependencies
- Use existing tools (Pyodide, Wazero, Javy) rather than building from scratch
- Prefer standard WASI interfaces over custom solutions
- Avoid introducing dependencies that won't work in Snowflake's environment

### 3. P67 Compatibility
- SDK host functions must mirror the existing P67 WorkflowSDK interface
- Workflows should be portable between WASM and current Node.js/Python runtimes
- Preserve LangGraph workflow patterns (StateGraph, async nodes)

### 4. Measurable Success Criteria
- Every phase must have quantifiable metrics (startup time, memory, throughput)
- Compare results against current Docker/process-based approach
- Document trade-offs explicitly

### 5. Security by Design
- WASM sandbox must prevent arbitrary filesystem access
- Network access only through SDK host functions
- No eval() or dynamic code execution outside sandbox

## Technical Guidelines

### Language Preferences
- Go for host runtime (Wazero integration)
- TypeScript for Javy experiments
- Python for Pyodide workflow tests

### Code Style
- Minimal comments (code should be self-documenting)
- Comprehensive README for each phase
- Benchmark scripts must be reproducible

### Testing Standards
- Each phase must include runnable validation tests
- Performance benchmarks with statistical significance (multiple runs)
- Comparison against baseline (current P67 implementation)

## Out of Scope
- Production deployment considerations
- Multi-tenant isolation
- Persistent state management
- Integration with Snowflake infrastructure

## Success Definition
This experiment succeeds if we can answer:
1. Can LangGraph workflows run in Pyodide?
2. What is the cold/warm start overhead vs Docker?
3. Is Wazero a viable Go runtime for Pyodide?
4. Can we compile TS workflows to WASM via Javy?
