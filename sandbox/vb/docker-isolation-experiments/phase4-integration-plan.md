# Phase 4: Production Integration Plan

> **Status**: PLANNED (not started)
> **Last Updated**: March 5, 2026

## Overview

Integrate container pooling and security hardening from Phase 1-2 experiments into P67's controld service.

---

## Prerequisites

- [ ] Phase 1 pooling benchmarks validated ✅
- [ ] Phase 2 security hardening tested ✅
- [ ] Phase 3 gVisor tested on Linux/SPCS (pending)
- [ ] Code review of existing DockerAdapter/Runner

---

## Integration Steps

### Step 1: Locate Existing Code

Find the current container execution code in controld:
```bash
# Expected locations
p67/controld/src/adapters/DockerAdapter.ts
p67/controld/src/runner/Runner.ts
p67/controld/src/services/WorkflowExecutor.ts
```

Key functions to modify:
- Container creation (replace with pool.acquire)
- Container cleanup (replace with pool.release)
- Workflow execution entry point

### Step 2: Add Pool Configuration

```typescript
// config/default.ts or environment variables
export interface ContainerPoolConfig {
  enabled: boolean;           // Feature flag
  minSize: number;            // Pre-warmed containers (default: 3)
  maxSize: number;            // Max concurrent (default: 20)
  idleTimeoutMs: number;      // Recycle idle containers (default: 300000)
  securityLevel: 'standard' | 'hardened' | 'gvisor';
  image: string;              // Container image
}

// Recommended defaults
const DEFAULT_POOL_CONFIG: ContainerPoolConfig = {
  enabled: false,             // Start disabled
  minSize: 3,
  maxSize: 20,
  idleTimeoutMs: 300000,      // 5 minutes
  securityLevel: 'hardened',
  image: 'p67-workflow-runner:latest',
};
```

### Step 3: Pool Lifecycle Management

```typescript
// In controld startup
class Controld {
  private containerPool?: ContainerPool;

  async start() {
    if (config.containerPool.enabled) {
      this.containerPool = new ContainerPool(config.containerPool);
      await this.containerPool.initialize();
      
      // Health check endpoint
      this.registerHealthCheck('container-pool', () => this.containerPool.getStats());
    }
  }

  async shutdown() {
    if (this.containerPool) {
      await this.containerPool.shutdown();
    }
  }
}
```

### Step 4: Modify Workflow Execution

**Before (current)**:
```typescript
async executeWorkflow(workflow: Workflow): Promise<Result> {
  const container = await docker.createContainer({...});
  await container.start();
  // ... execute workflow
  await container.remove();
  return result;
}
```

**After (with pooling)**:
```typescript
async executeWorkflow(workflow: Workflow): Promise<Result> {
  const entry = await this.containerPool.acquire();
  
  try {
    const result = await this.containerPool.executeInContainer(
      entry,
      workflow.command
    );
    return result;
  } finally {
    await this.containerPool.release(entry);
  }
}
```

### Step 5: Security Configuration

Apply hardening based on security level:

```typescript
const SECURITY_CONFIGS = {
  standard: {
    CapDrop: ['ALL'],
    SecurityOpt: ['no-new-privileges:true'],
    NetworkMode: 'none',
  },
  
  hardened: {
    CapDrop: ['ALL'],
    SecurityOpt: ['no-new-privileges:true'],
    ReadonlyRootfs: true,
    NetworkMode: 'none',
    Memory: 128 * 1024 * 1024,
    NanoCpus: 500_000_000,
    PidsLimit: 100,
    Tmpfs: {
      '/tmp': 'rw,noexec,nosuid,size=64m',
    },
  },
  
  gvisor: {
    // Same as hardened, plus:
    Runtime: 'runsc',
  },
};
```

---

## Metrics & Monitoring

### Pool Metrics to Track

| Metric | Description |
|--------|-------------|
| `pool_size` | Current number of pooled containers |
| `pool_in_use` | Containers currently executing workflows |
| `pool_acquire_latency_ms` | Time to acquire a container |
| `pool_hit_rate` | % of acquires served from pool (vs new) |
| `pool_exhausted_count` | Times pool reached max capacity |

### Health Check Endpoint

```typescript
GET /health/container-pool

Response:
{
  "status": "healthy",
  "poolSize": 5,
  "inUse": 2,
  "available": 3,
  "maxSize": 20,
  "acquireLatencyP50": 2,
  "acquireLatencyP99": 45
}
```

---

## Rollout Plan

### Phase A: Canary (1 week)
- Enable for 5% of traffic
- Monitor metrics, error rates
- Compare latency: pooled vs non-pooled

### Phase B: Gradual Rollout (2 weeks)
- Increase to 25%, 50%, 75%, 100%
- Adjust pool sizing based on load patterns

### Phase C: Cleanup
- Remove non-pooled code path
- Update documentation

---

## Risk Mitigation

### Risk 1: State Leakage Between Executions
**Mitigation**: 
- Clear `/tmp` and workflow directories on release
- Consider container recycling after N executions
- Add state verification checks

### Risk 2: Pool Exhaustion Under Load
**Mitigation**:
- Queue requests when pool exhausted (with timeout)
- Auto-scale pool size based on demand
- Alert on high exhaustion rate

### Risk 3: Container Crashes
**Mitigation**:
- Health check containers before returning to pool
- Remove crashed containers, replenish pool
- Circuit breaker for repeated failures

### Risk 4: Memory Leaks in Long-Running Containers
**Mitigation**:
- Max lifetime per container (e.g., 1 hour)
- Monitor memory usage, recycle if growing
- Periodic pool refresh

---

## Testing Requirements

### Unit Tests
- [ ] Pool initialization with min containers
- [ ] Acquire/release cycle
- [ ] Pool exhaustion handling
- [ ] Container cleanup on release

### Integration Tests
- [ ] Real LangGraph workflow execution
- [ ] Concurrent workflow execution
- [ ] Pool recovery after container crash
- [ ] Graceful shutdown with in-flight requests

### Load Tests
- [ ] Sustained load at expected QPS
- [ ] Burst traffic handling
- [ ] Pool sizing validation

### Security Tests
- [ ] Verify hardening applied correctly
- [ ] Container escape attempt (should fail)
- [ ] Network isolation verification
- [ ] Resource limit enforcement

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `controld/src/pool/ContainerPool.ts` | CREATE | Port from experiments |
| `controld/src/pool/types.ts` | CREATE | Type definitions |
| `controld/src/config/pool.ts` | CREATE | Pool configuration |
| `controld/src/adapters/DockerAdapter.ts` | MODIFY | Use pool |
| `controld/src/runner/Runner.ts` | MODIFY | Acquire/release pattern |
| `controld/src/health/poolHealth.ts` | CREATE | Health checks |
| `controld/tests/pool.test.ts` | CREATE | Unit tests |

---

## References

- [Phase 1 Benchmark Results](./benchmarks/results/pooling-benchmark.json)
- [Phase 2 Security Tests](./phase2-hardening/hardening.test.js)
- [Container Pool Implementation](./phase1-pooling/pool.js)
- [Security Audit Checklist](./phase2-hardening/audit-checklist.md)
