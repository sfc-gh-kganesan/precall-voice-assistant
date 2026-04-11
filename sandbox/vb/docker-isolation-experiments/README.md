# P67 Docker Isolation Experiments

## Goal
Optimize Docker-based workflow execution for P67 with focus on:
1. **Container pooling** - Eliminate cold start latency
2. **Security hardening** - Seccomp profiles, capability dropping
3. **gVisor integration** - Stronger isolation when needed
4. **Performance benchmarks** - Quantify improvements

---

## Current P67 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTROLD SERVICE                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Runner.ts                         │    │
│  │  - Spawns NEW container per workflow execution      │    │
│  │  - Cold start: ~1-2s per execution                  │    │
│  │  - No container reuse                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Problem**: Every workflow execution pays cold start cost.

---

## Experiment Plan

### Phase 1: Container Pooling (Priority 1)
**Goal**: Pre-warm containers and reuse them for near-instant execution.

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTROLD SERVICE                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               ContainerPool                         │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐               │    │
│  │  │ Warm #1 │ │ Warm #2 │ │ Warm #3 │  ...          │    │
│  │  │ (idle)  │ │ (idle)  │ │ (in-use)│               │    │
│  │  └─────────┘ └─────────┘ └─────────┘               │    │
│  │                                                     │    │
│  │  acquire() → ~50ms (warm) vs ~1-2s (cold)          │    │
│  │  release() → reset state, return to pool           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Deliverables**:
- [ ] `pool.ts` - Container pool manager
- [ ] `benchmarks/cold-vs-warm.ts` - Measure improvement
- [ ] Integration with existing `DockerAdapter`

### Phase 2: Security Hardening (Priority 2)
**Goal**: Minimize attack surface while maintaining functionality.

**Hardening layers**:
1. **Seccomp profile** - Allowlist only required syscalls
2. **Capability dropping** - `CAP_DROP=ALL`
3. **Read-only root** - `--read-only`
4. **No new privileges** - `--security-opt=no-new-privileges`
5. **Resource limits** - Memory, CPU, PIDs
6. **Network isolation** - `--network=none` or restricted

**Deliverables**:
- [ ] `seccomp-profile.json` - Custom profile for Python/LangGraph
- [ ] `hardened-config.ts` - Docker run configuration
- [ ] Security audit checklist

### Phase 3: gVisor Integration (Priority 3)
**Goal**: Evaluate gVisor (runsc) for stronger isolation.

```bash
# Run with gVisor instead of runc
docker run --runtime=runsc ...
```

**Deliverables**:
- [ ] gVisor installation guide for dev/SPCS
- [ ] `benchmarks/runc-vs-gvisor.ts` - Performance comparison
- [ ] Compatibility testing with LangGraph workflows

### Phase 4: Production Integration
**Goal**: Integrate improvements into P67 controld service.

**Deliverables**:
- [ ] Updated `DockerAdapter` with pooling
- [ ] Configuration options for security level
- [ ] Monitoring/metrics for pool health

---

## Directory Structure

```
docker-isolation/
├── README.md                    # This file
├── phase1-pooling/
│   ├── pool.ts                  # Container pool implementation
│   ├── pool.test.ts             # Unit tests
│   └── benchmark.ts             # Cold vs warm benchmarks
├── phase2-hardening/
│   ├── seccomp-profile.json     # Custom seccomp allowlist
│   ├── Dockerfile.hardened      # Hardened base image
│   └── audit-checklist.md       # Security checklist
├── phase3-gvisor/
│   ├── install.md               # gVisor setup guide
│   └── benchmark.ts             # runc vs gVisor comparison
└── benchmarks/
    └── results/                 # Benchmark output data
```

---

## Quick Start

```bash
cd sandbox/vb/docker-isolation-experiments

# Phase 1: Test container pooling
cd phase1-pooling
npm install
npm test

# Run benchmarks
npm run benchmark
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Cold start latency | ~1-2s | N/A (unavoidable) |
| Warm start latency | N/A | <100ms |
| Pool hit rate | N/A | >90% |
| Memory per pooled container | N/A | <150MB |
| Syscalls allowed | ~300 | <100 |

---

## References

- [P67 WASM Research](../wasm-sandbox-experiments/README.md) - Why we chose Docker
- [gVisor Documentation](https://gvisor.dev/docs/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Seccomp BPF](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
