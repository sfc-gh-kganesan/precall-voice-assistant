# Agent Handoff: Docker Isolation Experiments

> Last updated: March 5, 2026
> Status: Phases 1-2 complete, Phase 3 needs Linux, Phase 4 planned

## What This Is

Experiments to optimize Docker-based workflow execution for P67:
- **Container pooling** — Reuse warm containers instead of cold-starting each time
- **Security hardening** — Seccomp, capability dropping, network isolation
- **gVisor** — User-space kernel for stronger isolation (optional)

## Current Status

| Phase | Status | Result |
|-------|--------|--------|
| Phase 1: Pooling | ✅ Done | **2.1x faster** (95ms → 46ms) |
| Phase 2: Hardening | ✅ Done | **20-28% faster** + all security tests pass |
| Phase 3: gVisor | ⏳ Ready | Scripts written, needs Linux to test |
| Phase 4: Integration | 📋 Planned | See `phase4-integration-plan.md` |

## Key Results

### Phase 1: Container Pooling
```
Cold start (new container):  95ms mean
Warm start (pooled):         46ms mean
Speedup:                     2.1x
```

### Phase 2: Security Hardening
```
| Level              | Mean   | vs Baseline |
|--------------------|--------|-------------|
| Baseline           | 207ms  | -           |
| Level 1 (basic)    | 149ms  | -28%        |
| Level 2 (hardened) | 162ms  | -22%        |
| Level 2 + seccomp  | 151ms  | -27%        |
```

**Surprising**: Hardening is FASTER because `NetworkMode: none` skips network stack.

## How to Run

```bash
# Phase 1: Pooling tests
cd phase1-pooling
npm install
npm test              # Run unit tests
npm run benchmark     # Run cold vs warm benchmark

# Phase 2: Hardening tests
cd phase2-hardening
npm install
npm test              # Run security tests
npm run benchmark     # Compare security levels

# Phase 3: gVisor (Linux only)
cd phase3-gvisor
npm install
npm run check         # Check if gVisor is available
npm run benchmark     # Compare runc vs runsc
```

## Important Files

| File | Purpose |
|------|---------|
| `phase1-pooling/pool.js` | ContainerPool class — acquire/release/execute |
| `phase1-pooling/pool.test.js` | 7 unit tests for pooling |
| `phase1-pooling/benchmark.js` | Cold vs warm latency comparison |
| `phase2-hardening/seccomp-profile.json` | Syscall allowlist for Python |
| `phase2-hardening/hardening.test.js` | 10 security tests |
| `phase2-hardening/audit-checklist.md` | Security audit checklist |
| `phase3-gvisor/check-gvisor.js` | Detect if runsc is available |
| `phase4-integration-plan.md` | Full production integration guide |
| `benchmarks/results/*.json` | Raw benchmark data |

## What's Left To Do

### If continuing gVisor testing:
1. Get access to Linux machine or SPCS
2. Install gVisor: `apt-get install runsc`
3. Run `npm run check` to verify
4. Run `npm run benchmark` to compare runc vs runsc

### If integrating into P67:
1. Read `phase4-integration-plan.md` thoroughly
2. Find existing DockerAdapter/Runner in controld
3. Port `pool.js` to TypeScript
4. Add feature flag for gradual rollout
5. Add health checks and metrics

## Gotchas / Things to Know

1. **Docker image required**: Tests use `python:3.11-slim` — must be pulled first
2. **macOS limitation**: gVisor doesn't work on Docker Desktop (no KVM)
3. **State cleanup**: Pool releases clean `/tmp` but consider container recycling after N uses
4. **Network=none is good**: It speeds things up AND improves security

## Benchmark Data Location

Raw JSON results in `benchmarks/results/`:
- `pooling-benchmark.json` — Phase 1 results
- `hardening-benchmark.json` — Phase 2 results
- `workflow-simulation.json` — Simulated LangGraph execution
- `gvisor-benchmark.json` — Phase 3 results (when run on Linux)
