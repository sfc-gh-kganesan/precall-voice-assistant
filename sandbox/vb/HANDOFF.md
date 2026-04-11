# Agent Handoff: Sandbox Experiments

> Last updated: March 5, 2026
> Previous agent context: Docker isolation & WASM sandbox evaluation for P67

## Quick Links
- [Docker Isolation Experiments](./docker-isolation-experiments/HANDOFF.md)
- [WASM Sandbox Experiments](./wasm-sandbox-experiments/HANDOFF.md)

## TL;DR

Evaluated sandboxing approaches for P67 workflow execution (LangGraph/Python).

**Conclusion**: Docker + container pooling + security hardening is the right approach.
WASM (Pyodide) works but has LangGraph version constraints.

## Overall Status

| Experiment | Status | Recommendation |
|------------|--------|----------------|
| Docker Pooling | ✅ Complete | **USE THIS** - 2.1x faster |
| Docker Hardening | ✅ Complete | **USE THIS** - 20-28% faster + secure |
| gVisor | ⏳ Ready | Test on Linux/SPCS |
| WASM/Pyodide | ✅ Research complete | Fallback option only |

## Key Decisions Made

1. **Why Docker over WASM?**
   - LangGraph requires native Python with specific pydantic versions
   - Pyodide has version constraints that limit LangGraph compatibility
   - Docker pooling achieves comparable startup times (~46ms warm)

2. **Why not V8 Isolates?**
   - JavaScript only — can't run Python/LangGraph
   - CPU limits (~50ms) conflict with LLM workflow durations

3. **Security hardening is FREE**
   - `NetworkMode: none` actually speeds things up (no network stack setup)
   - No measurable overhead from seccomp, CAP_DROP, read-only fs

## For Future Agents

If continuing this work:

1. **To test gVisor**: Need Linux machine or SPCS (not macOS)
   ```bash
   cd docker-isolation-experiments/phase3-gvisor
   npm run check  # Verify gVisor available
   npm run benchmark
   ```

2. **To integrate into P67**: See `docker-isolation-experiments/phase4-integration-plan.md`

3. **To run existing benchmarks**:
   ```bash
   cd docker-isolation-experiments/phase1-pooling
   npm test && npm run benchmark
   ```

## File Structure

```
sandbox/vb/
├── docker-isolation-experiments/
│   ├── phase1-pooling/        # Container pool (2.1x faster) ✅
│   ├── phase2-hardening/      # Security hardening ✅
│   ├── phase3-gvisor/         # gVisor scripts (needs Linux) ⏳
│   ├── phase4-integration-plan.md  # Production integration plan
│   └── benchmarks/results/    # Benchmark JSON data
├── wasm-sandbox-experiments/
│   ├── phase1-pyodide-node/   # Pyodide in Node.js ✅
│   ├── phase2-go-wazero/      # Go orchestration ✅
│   └── README.md              # Full research documentation
└── HANDOFF.md                 # This file
```
