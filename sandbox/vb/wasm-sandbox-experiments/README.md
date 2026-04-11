# P67 WASM Sandbox Experiments

## Goal
Evaluate WASM-based sandboxing as an alternative to Docker containers for P67 workflow execution.

---

## 🏁 Final Conclusion: Docker Recommended Over WASM

**Recommendation**: Proceed with Docker-based workflow execution. WASM does not provide sufficient benefits to justify the added complexity and version constraints.

### Summary

| Factor | WASM (Pyodide) | Docker |
|--------|----------------|--------|
| **LangGraph support** | v0.0.38 only (Jan 2024) | Any version ✅ |
| **Cold start** | ~2-3s | ~1-2s ✅ |
| **Architecture complexity** | Go → Node.js → Pyodide | Go → Docker ✅ |
| **Native extensions** | Pre-compiled only | Full support ✅ |
| **Maintenance burden** | High (version pinning) | Low ✅ |

### Why Not WASM

1. **LangGraph Version Lock**: Only `langgraph==0.0.38` works due to `uuid-utils` native dependency in newer versions. This is over 2 years behind current releases.

2. **Emscripten Requirement**: Pyodide uses Emscripten (not WASI), requiring a JavaScript runtime. This means Go cannot run Pyodide directly—we'd need `Go → Node.js subprocess → Pyodide`, adding complexity without removing Docker-like subprocess overhead.

3. **No Startup Advantage**: Cold starts are comparable (~2-3s vs ~1-2s), and with container pooling, Docker warm starts can be competitive.

4. **SDK Host Functions Still Require IPC**: Whether WASM or Docker, SDK calls (`execute_query`, `cortex_complete`, etc.) require IPC from the sandboxed process back to controld. WASM doesn't eliminate this.

---

## P67 Orchestration Architecture

**Q: Where does orchestration happen?**

**A: Controld is the orchestration host.**

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTROLD SERVICE                         │
│                    (TypeScript/Fastify)                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Runner.ts                         │    │
│  │  - Loads workflow manifest                          │    │
│  │  - Spawns Docker container via RuntimeAdapter       │    │
│  │  - Handles IPC (NDJSON over stdin/stdout)           │    │
│  │  - Manages interrupts (human-in-the-loop)           │    │
│  │  - Processes SDK host function requests             │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              DockerAdapter.ts                       │    │
│  │  spawn(): docker run --rm -i -v <workflow>:/workflow│    │
│  │  sendMessage(): JSON → stdin                        │    │
│  │  onMessage(): stdout → JSON                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DOCKER CONTAINER                         │
│                    (p67-runner image)                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Go Supervisor (auto-detects Python/TypeScript)     │    │
│  │        │                                            │    │
│  │        ├── Python: runner_host.py                   │    │
│  │        │      └── User workflow (LangGraph)         │    │
│  │        │                                            │    │
│  │        └── TypeScript: runner-host.ts               │    │
│  │               └── User workflow (LangGraph.js)      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  IPC Protocol: NDJSON over stdin/stdout                     │
│  Messages: RunWorkflow, Result, Interrupt, ResumeInterrupt  │
└─────────────────────────────────────────────────────────────┘
```

**Key files**:
- `services/controld/src/lib/runner.ts` - Main orchestration logic
- `services/controld/src/lib/runtime/adapter.ts` - Docker spawning & IPC
- `services/controld/src/lib/runtime/schema.ts` - Message types

---

## Docker Alternatives for Lightweight Isolation

If Docker overhead becomes a concern, consider these alternatives:

### 1. gVisor (runsc) - Recommended
**What**: User-space kernel that intercepts syscalls, provides OCI runtime compatibility.

```bash
# Run with gVisor instead of runc
docker run --runtime=runsc ...
```

| Pros | Cons |
|------|------|
| Drop-in OCI replacement | ~10-30% CPU overhead |
| Strong syscall filtering | Not all syscalls supported |
| Used by GKE Sandbox | Requires host installation |

**Best for**: Production SPCS if syscall overhead is acceptable.

### 2. Firecracker microVMs
**What**: Lightweight VMs (~125ms boot) used by AWS Lambda/Fargate.

| Pros | Cons |
|------|------|
| True VM isolation | Requires KVM support |
| ~125ms cold start | More complex orchestration |
| Memory ballooning | Not OCI-compatible directly |

**Best for**: If you need VM-level isolation and have KVM access.

### 3. Container Pooling (Recommended First Step)
**What**: Pre-warm Docker containers and reuse them.

```typescript
// Example: Pool of warm containers
class ContainerPool {
  private pool: ChildProcess[] = [];
  
  async getWarmContainer(): Promise<ChildProcess> {
    if (this.pool.length > 0) {
      return this.pool.pop()!; // ~50ms
    }
    return this.spawnNew(); // ~1-2s cold start
  }
  
  release(container: ChildProcess): void {
    // Reset state and return to pool
    this.pool.push(container);
  }
}
```

| Pros | Cons |
|------|------|
| No infrastructure changes | Memory usage for pooled containers |
| ~50-100ms warm start | State cleanup complexity |
| Works with existing Docker | Pool size tuning required |

**Best for**: Immediate improvement without infrastructure changes.

### 4. Kata Containers
**What**: Lightweight VMs that look like containers (OCI-compatible).

| Pros | Cons |
|------|------|
| OCI compatible | Requires KVM/nested virt |
| VM-level isolation | Higher memory overhead |
| Works with Kubernetes | ~500ms startup |

### 5. Bubblewrap (bwrap)
**What**: Unprivileged sandboxing using Linux namespaces (used by Flatpak).

```bash
bwrap --ro-bind /usr /usr --proc /proc --dev /dev \
      --bind /workflow /workflow \
      python /workflow/main.py
```

| Pros | Cons |
|------|------|
| No root required | Linux-only |
| Very fast (~10ms) | Less isolation than containers |
| Minimal overhead | Manual setup of mounts |

**Best for**: Development environments or trusted workflows.

### Recommendation Order

1. **Container Pooling** - Implement first, biggest bang for buck
2. **gVisor** - If stronger isolation needed on SPCS
3. **Firecracker** - If VM-level isolation required and KVM available

---

## Results Summary

### ✅ Phase 1: LangGraph in Pyodide - WORKS

| Test | Result |
|------|--------|
| LangGraph import | ✅ Works (v0.0.38) |
| StateGraph compile | ✅ Works |
| Workflow execution | ✅ Works with `await ainvoke()` |
| Host function calls | ✅ ~0.09ms overhead |
| Cold start | ~900ms |

**Key constraints**:
- Must use `langgraph==0.0.38` (newer versions require `uuid-utils` native code)
- Must use `await app.ainvoke()` directly (not `invoke()` or `run_until_complete()`)
- Pyodide 0.29.3 required (has pydantic 2.12.5)

### ✅ Phase 2: Go Integration - WORKS (with Node.js)

**Finding**: Pyodide is Emscripten-based, NOT WASI-compatible. Cannot run directly in Wazero.

**Solution**: Go orchestrates Node.js subprocess running Pyodide:
```
Go Control Plane
  └── Node.js subprocess (IPC via JSON over stdin/stdout)
        └── Pyodide (CPython in WASM)
              └── LangGraph workflow
                    └── Host function calls → Go
```

## Research Summary

### Key Finding: `langchain-sandbox` exists (but archived)
LangChain built and [open-sourced](https://github.com/langchain-ai/langchain-sandbox) a Pyodide-based sandbox:
- **Architecture**: Python → Deno subprocess → Pyodide (CPython compiled to WASM)
- **Status**: Archived Jan 2026, "no longer maintained"
- **Reason for deprecation**: LangChain recommends "sandbox APIs or LLM provider APIs" instead

**Limitations discovered**:
| Issue | Impact on P67 |
|-------|---------------|
| Cold start ~2-3s | Similar to Docker, negates lightweight advantage |
| No file system access | OK for P67 (workflows shouldn't touch filesystem) |
| Network via `httpx.AsyncClient` only | Would need SDK host functions anyway |
| Asyncio works but server-side blocking is problematic | LangGraph uses async heavily |

### Pyodide vs Docker Comparison

| Factor | Pyodide (WASM) | Docker |
|--------|----------------|--------|
| Cold start | ~2-3s | ~1-2s |
| Warm start (pooled) | ~50-100ms | ~500ms-1s |
| Memory per instance | ~50-100MB | ~100-200MB |
| Python compatibility | Most pure Python | Full CPython |
| Native extensions | Pre-compiled only | Full support |
| Isolation | WASM sandbox | OS-level |

### Wazero (Go WASM Runtime) Production Lessons
From [Arcjet's blog post](https://blog.arcjet.com/lessons-from-running-webassembly-in-production-with-go-wazero/):
- Pre-compile WASM modules at startup (takes seconds, amortized over requests)
- Use `go:embed` for WASM binaries
- Use [Wizer](https://github.com/bytecodealliance/wizer) for pre-initialization snapshots
- Use `wasm-opt` for size/performance optimization
- Profiling is difficult (wzprof exists but limited)

## Experiment Plan

### Phase 1: Validate Pyodide + LangGraph (1-2 days)
**Goal**: Confirm LangGraph workflows can run in Pyodide

```
experiments/wasm/
├── phase1-pyodide-node/
│   ├── package.json           # Node.js project
│   ├── runner.js              # Pyodide runner + instance pool
│   ├── tests/
│   │   ├── basic_python.js    # Basic Pyodide execution
│   │   ├── langgraph_import.js # LangGraph import test
│   │   ├── stateful_workflow.js # StateGraph test
│   │   └── host_functions.js  # SDK host function test
│   └── workflows/
│       └── sample_workflow.py # P67-style test workflow
```

**Tests**:
1. Can we import `langgraph` in Pyodide?
2. Can we run a simple StateGraph?
3. Can we call host functions from Pyodide for SDK operations?
4. What's the cold start time? Warm start time?

### Phase 2: Go + Wazero Integration (2-3 days)
**Goal**: Run Pyodide from Go using Wazero instead of Deno

```
experiments/wasm/
├── phase2-go-wazero/
│   ├── main.go                # Go host with Wazero
│   ├── host_functions.go      # SDK host function implementations
│   ├── pyodide_pool.go        # Instance pooling for warm starts
│   └── test_workflow.py       # Sample P67 workflow
```

**Architecture**:
```
┌─────────────────────────────────────────────────┐
│              Go Control Plane                   │
│  ┌───────────────────────────────────────────┐  │
│  │           Wazero Runtime                  │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │  Pyodide WASM (~25MB)               │  │  │
│  │  │  ├── CPython interpreter            │  │  │
│  │  │  └── User workflow.py               │  │  │
│  │  └─────────────────────────────────────┘  │  │
│  │              ↕ Host Functions              │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │  p67_execute_query()                │  │  │
│  │  │  p67_cortex_complete()              │  │  │
│  │  │  p67_http_request()                 │  │  │
│  │  └─────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Phase 3: TypeScript via Javy (1-2 days)
**Goal**: Compile TS workflows to WASM using Javy

```
experiments/wasm/
├── phase3-javy-typescript/
│   ├── build.sh               # TS → JS → WASM pipeline
│   ├── workflow.ts            # Sample P67 TS workflow
│   ├── sdk_shim.ts            # SDK calls → host function bridge
│   └── main.go                # Go host running Javy WASM
```

**Pipeline**:
```
workflow.ts → esbuild → bundle.js → javy compile → workflow.wasm
```

### Phase 4: Performance Benchmarks (1 day)
**Goal**: Quantify startup time, memory, and throughput

**Metrics to capture**:
- Cold start latency (first execution)
- Warm start latency (pooled instance)
- Memory per instance
- Throughput (executions/second)
- Comparison vs current Node.js/Python process model

## Open Questions (ANSWERED)

1. **Can Pyodide run in Wazero?**
   - ❌ **NO** - Pyodide is Emscripten-based, requires JS runtime
   - Solution: Go → Node.js subprocess → Pyodide

2. **LangGraph async patterns**
   - ✅ **SOLVED** - Use `await app.ainvoke()` directly in `runPythonAsync()`
   - Don't use `invoke()` (threading) or `run_until_complete()` (JSPI)

3. **SDK host function protocol**
   - ✅ **SOLVED** - JSON over stdin/stdout IPC
   - ~0.09ms overhead per call

4. **Instance pooling strategy**
   - Implemented in `runner.js` (PyodidePool class)
   - Warm start: ~0.05ms

## Getting Started

### Prerequisites
```bash
# Node.js 18+ (for Phase 1)
node --version  # Should be 18+

# Go 1.21+ (for Phase 2+)
brew install go

# Javy (for Phase 3)
cargo install javy-cli
```

### Run Phase 1 Tests
```bash
cd phase1-pyodide-node
npm install
node tests/langgraph_full.js    # Full LangGraph workflow test
```

### Run Phase 2 Tests
```bash
cd phase2-go-wazero
npm install
npm test                        # Validates Go → Node.js → Pyodide → LangGraph
go build && ./phase2-test       # Go host function demo
```

## Spec-Driven Development

This experiment uses [spec-kit](https://github.com/github/spec-kit) for structured development.

### Artifacts
```
.specify/
├── memory/constitution.md                    # Project principles
└── features/001-wasm-sandbox-eval/
    ├── spec.md                               # Requirements & user stories
    ├── plan.md                               # Implementation plan
    └── tasks.md                              # Actionable task list
```

### Workflow
1. Review `spec.md` for requirements
2. Follow `plan.md` for architecture decisions
3. Track progress in `tasks.md`

---

## Deep Research: WASM Runtime Alternatives to Wazero

### The Core Problem: Native Extensions

The fundamental blocker for running LangGraph in any WASM runtime is **native extensions**:

| Package | Native Code | Why It's Required |
|---------|-------------|-------------------|
| `pydantic-core` | Rust → C extension | Data validation (LangGraph uses Pydantic heavily) |
| `orjson` | Rust → C extension | Fast JSON parsing |
| `pyyaml` (libyaml) | C extension | YAML parsing |
| `uuid-utils` | Rust → C extension | UUID generation (LangGraph 0.0.39+) |

**Key insight**: These packages need to be compiled specifically for the WASM target. There are only two approaches:
1. **Pyodide** - Maintains pre-compiled WASM wheels for 200+ packages (Emscripten-based)
2. **WASI builds** - Compile from source targeting `wasm32-wasi` (limited package support)

### WASM Runtime Comparison for Python

| Runtime | Language | WASI Support | Can Run Pyodide? | Can Run WASI Python? | Native Extensions |
|---------|----------|--------------|------------------|---------------------|-------------------|
| **Wazero** | Go | WASI Preview 1 | ❌ No (needs JS) | ✅ Yes | ❌ Pure Python only |
| **Wasmtime** | Rust | WASI 0.1, 0.2, 0.3 | ❌ No (needs JS) | ✅ Yes | ❌ Pure Python only |
| **Wasmer** | Rust | WASI + WASIX | ❌ No (needs JS) | ✅ Yes (WASIX) | ⚠️ Some (via WASIX) |
| **WasmEdge** | C++ | WASI + Extensions | ❌ No (needs JS) | ✅ Yes | ⚠️ Limited |
| **V8/Node.js** | C++ | N/A (JS runtime) | ✅ Yes | N/A | ✅ Via Pyodide wheels |

### Why No Alternative to Wazero Solves the Problem

**All WASI-based runtimes have the same limitation**: They can only run **pure Python** code or packages with WASI-compiled native extensions.

#### Option 1: CPython WASI Build (wasmtime/wasmer/wazero)

**What it is**: CPython compiled to `wasm32-wasi` target (official Python support per PEP 816).

```bash
# Example: Running CPython on Wasmtime
wasmtime run --mapdir /::$PWD python-3.14.wasm -- my_script.py
```

**Limitations**:
- ✅ Works for pure Python (stdlib works)
- ❌ No `pydantic-core` - not compiled for WASI
- ❌ No `orjson` - not compiled for WASI
- ❌ No threads (WASI 0.1 limitation, WASI 0.3 adds threads but not stable)
- ❌ No sockets (WASI 0.1 limitation)

**LangGraph compatibility**: ❌ **Cannot run LangGraph** - requires pydantic-core

#### Option 2: Wasmer WASIX (Extended WASI)

**What it is**: Wasmer's extended WASI with threads, sockets, and dynamic linking.

From Wasmer's blog (Sep 2025):
> "After months of hard work, today we're thrilled to announce full Python support in Wasmer Edge (Beta) powered by WebAssembly and WASIX."

**What Wasmer WASIX adds**:
- ✅ Threads (pthreads)
- ✅ Sockets
- ✅ Dynamic linking (`dlopen`/`dlsym`)
- ✅ `libffi` support (for ctypes)
- ✅ Their own Python Package Index with WASIX-compiled wheels

**Supported packages** (from wasmer.io):
- FastAPI, Django, Flask, Starlette
- LangChain, Streamlit
- SQLAlchemy, numpy, pandas, pillow

**LangGraph compatibility**: ⚠️ **Unknown** - LangGraph not explicitly listed. Would need to verify if `pydantic-core` WASIX wheel exists.

**Architecture implications for P67**:
```
Go Control Plane
  └── Wasmer CLI/Runtime (not embeddable in Go easily)
        └── WASIX Python
              └── LangGraph (if pydantic-core available)
```

**Problem**: Wasmer is Rust-based, not easily embeddable in Go. Would need subprocess.

#### Option 3: componentize-py (WASIp2 Components)

**What it is**: Tool to compile Python apps to WebAssembly Components (WASIp2).

```bash
pip install componentize-py
componentize-py -d workflow.wit -w workflow componentize app.py -o workflow.wasm
```

**Limitations**:
- ✅ Works for pure Python
- ❌ No native extension support (same limitation as WASI)
- ❌ Components are self-contained, no dynamic imports
- ❌ All imports must be resolved at build time

**LangGraph compatibility**: ❌ **Cannot run LangGraph** - no pydantic-core

#### Option 4: RustPython

**What it is**: Python interpreter written in Rust, compilable to WASM.

**Limitations**:
- ✅ Can compile to `wasm32-wasi` target
- ❌ Only supports Python 3.10 feature set
- ❌ Many stdlib modules missing
- ❌ No C extension support at all
- ❌ Compatibility issues with modern Python packages

**LangGraph compatibility**: ❌ **Cannot run LangGraph**

### The Fundamental Architecture Problem

```
┌─────────────────────────────────────────────────────────────────┐
│                     PYTHON EXECUTION OPTIONS                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐     ┌─────────────────────────────────┐   │
│   │   Emscripten    │     │           WASI                  │   │
│   │   (Pyodide)     │     │  (wasmtime/wasmer/wazero/etc)   │   │
│   ├─────────────────┤     ├─────────────────────────────────┤   │
│   │ ✅ pydantic-core│     │ ❌ pydantic-core (no wheel)     │   │
│   │ ✅ orjson       │     │ ❌ orjson (no wheel)            │   │
│   │ ✅ numpy        │     │ ❌ numpy (no wheel)*            │   │
│   │ ✅ LangGraph    │     │ ❌ LangGraph                    │   │
│   ├─────────────────┤     ├─────────────────────────────────┤   │
│   │ Requires:       │     │ Can run in:                     │   │
│   │ JS Runtime      │     │ Any WASI runtime                │   │
│   │ (Node/Deno/V8)  │     │ (wazero/wasmtime/wasmer/etc)    │   │
│   └────────┬────────┘     └─────────────────────────────────┘   │
│            │                                                    │
│            ▼                                                    │
│   ┌─────────────────┐                                           │
│   │ Go Control Plane│                                           │
│   │ must spawn      │     * WASIX (Wasmer) has some native      │
│   │ Node.js process │       packages but LangGraph status       │
│   └─────────────────┘       unknown                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Conclusion: Same Issues With All Wazero Alternatives

| Runtime | Embeds in Go? | Runs Pyodide? | Runs WASI Python? | Runs LangGraph? |
|---------|---------------|---------------|-------------------|-----------------|
| Wazero | ✅ Native | ❌ | ✅ | ❌ |
| Wasmtime | ⚠️ C bindings | ❌ | ✅ | ❌ |
| Wasmer | ⚠️ C bindings | ❌ | ✅ (WASIX) | ⚠️ Unknown |
| WasmEdge | ⚠️ C bindings | ❌ | ✅ | ❌ |

**The core problem remains**: 
1. Pyodide (with native wheels) requires a JavaScript runtime
2. WASI Python (without native wheels) cannot run LangGraph
3. No WASM runtime can embed Pyodide directly

**Only viable WASM paths for LangGraph**:
1. **Go → Node.js subprocess → Pyodide** (what we prototyped)
2. **Wasmer WASIX** (if LangGraph works - needs verification)

Both add complexity comparable to or exceeding Docker.

---

## Comprehensive Workflow Isolation Alternatives

This section documents all isolation mechanisms considered as alternatives to Docker for P67 workflow execution, ordered from strongest isolation to lightest.

### The Isolation Spectrum

```
Isolation Strength →                Attack Surface ↓

Hardware VMs    MicroVMs     User-space    Containers    Process      None
(Firecracker)   (Kata)       Kernel        (Docker)      Sandbox
                             (gVisor)                    (nsjail)
     │              │            │              │            │           │
     ▼              ▼            ▼              ▼            ▼           ▼
  Slowest       Fast         Moderate       Fast         Fastest     Native
  Strongest     Strong       Strong         Moderate     Weak        None
  ~125ms        ~500ms       ~50-100ms      ~1-2s        ~10ms       0ms
```

### 1. Hardware Virtualization (Strongest Isolation)

#### Intel SGX / ARM TrustZone
**What**: Hardware enclaves that isolate code at the CPU level.

| Aspect | Details |
|--------|---------|
| Security | Strongest possible - hardware-enforced memory encryption |
| Use case | Confidential computing, secrets processing |
| Limitations | Limited enclave memory, complex programming model |
| P67 fit | ❌ Overkill - not practical for workflow execution |

**Verdict**: Too specialized for general workflow isolation.

### 2. MicroVMs (Strong VM Isolation, Fast Boot)

#### Firecracker
**What**: Lightweight VMM from AWS, powers Lambda/Fargate. Boots VMs in ~125ms with only 5 emulated devices.

| Pros | Cons |
|------|------|
| True hardware isolation (KVM) | Requires KVM access |
| ~125ms cold start | No GPU passthrough |
| ~5MB memory overhead | Not OCI-compatible |
| Rust codebase (~50k LOC) | Custom orchestration needed |

**Architecture**:
```
┌─────────────────────────────────────┐
│          Host Kernel (KVM)          │
├─────────────────────────────────────┤
│      Firecracker VMM (Rust)         │
│  ┌─────────────────────────────────┐│
│  │         Guest Kernel            ││
│  │  ┌───────────────────────────┐  ││
│  │  │    User Workflow          │  ││
│  │  │    (LangGraph)            │  ││
│  │  └───────────────────────────┘  ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

**P67 fit**: ⚠️ Viable if KVM is available on SPCS, but adds orchestration complexity.

#### Kata Containers
**What**: OCI-compatible containers backed by lightweight VMs.

| Pros | Cons |
|------|------|
| OCI compatible (works with K8s) | ~500ms startup |
| VM-level isolation | Higher memory (~30-50MB) |
| Supports Firecracker, Cloud Hypervisor, QEMU | Requires nested virt |

**P67 fit**: ✅ Best of both worlds if nested virtualization is available.

### 3. User-Space Kernels (Strong Isolation, Moderate Overhead)

#### gVisor (runsc)
**What**: User-space kernel (Sentry) written in Go that intercepts syscalls before they reach the host kernel.

```
┌─────────────────────────────────────┐
│           Untrusted Code            │
│     (LangGraph Workflow)            │
└─────────────────┬───────────────────┘
                  │ ~340 syscalls
                  ▼
┌─────────────────────────────────────┐
│      gVisor Sentry (User-space)     │
│      Reimplements ~200 syscalls     │
│      in Go (memory-safe)            │
└─────────────────┬───────────────────┘
                  │ ~70 syscalls only
                  ▼
┌─────────────────────────────────────┐
│          Host Kernel                │
│    (Dramatically reduced attack     │
│     surface)                        │
└─────────────────────────────────────┘
```

| Pros | Cons |
|------|------|
| Drop-in OCI runtime | 10-30% I/O overhead |
| No KVM required | Some syscalls unsupported |
| Used by GKE Sandbox | Adds dependency |
| Memory-safe (Go) | |

**P67 fit**: ✅ **Recommended** if stronger isolation needed on SPCS.

### 4. Containers (Moderate Isolation)

#### Docker/OCI (Current P67 Approach)
**What**: Linux namespaces + cgroups + seccomp for process isolation.

| Isolation Primitive | What It Does | Security Boundary? |
|--------------------|--------------|--------------------|
| **Namespaces** | Visibility walls (PID, mount, network) | ❌ Not a security boundary |
| **Cgroups** | Resource limits (CPU, memory) | ❌ DoS prevention only |
| **Seccomp-BPF** | Syscall filtering | ⚠️ Reduces attack surface |
| **Capabilities** | Permission dropping | ⚠️ Defense in depth |

**Key insight**: Containers share the host kernel. A kernel exploit escapes all containers on that host.

**Docker hardening for P67**:
```yaml
# Recommended Docker settings for P67
security_opt:
  - no-new-privileges:true
  - seccomp:custom-profile.json
cap_drop:
  - ALL
read_only: true
network_mode: none  # Or restricted
tmpfs:
  /tmp: rw,noexec,nosuid,size=64m
```

### 5. Lightweight Process Sandboxing

#### nsjail (Google)
**What**: Lightweight isolation using namespaces, cgroups, seccomp, and rlimits. Used for CTF challenges and fuzzing.

| Pros | Cons |
|------|------|
| ~10ms startup | Requires careful configuration |
| Very lightweight | Not OCI compatible |
| Excellent seccomp integration | Linux only |
| Battle-tested (Google uses it) | |

**Example**:
```bash
nsjail \
  --chroot /srv/workflow \
  --user 65534 --group 65534 \
  --time_limit 60 \
  --rlimit_as 512 \
  --rlimit_cpu 10 \
  --seccomp_string 'ALLOW { read, write, ... } DEFAULT KILL' \
  -- python /srv/workflow/main.py
```

**P67 fit**: ⚠️ Very fast, but requires significant configuration work.

#### Bubblewrap (bwrap)
**What**: Unprivileged sandboxing using user namespaces. Powers Flatpak.

| Pros | Cons |
|------|------|
| No root required | Manual mount setup |
| ~10ms startup | Less isolation than containers |
| Used by Flatpak at scale | |

**Example**:
```bash
bwrap \
  --ro-bind /usr /usr \
  --ro-bind /lib64 /lib64 \
  --proc /proc \
  --dev /dev \
  --bind /workflow /workflow \
  --unshare-pid \
  --new-session \
  python /workflow/main.py
```

**P67 fit**: ⚠️ Good for development, may be too weak for production.

#### Firejail
**What**: Desktop application sandboxing with many pre-built profiles.

| Pros | Cons |
|------|------|
| Easy to use | Desktop-focused |
| Many profiles | Large attack surface |
| Pulseaudio/X11 support | Less auditable |

**P67 fit**: ❌ Not suited for server workloads.

### 6. Language/Runtime-Level Isolation

#### V8 Isolates (Cloudflare Workers approach)
**What**: JavaScript isolation using V8's built-in sandbox (used by Cloudflare Workers).

```
┌─────────────────────────────────────┐
│          V8 Engine Process          │
│  ┌─────────────┐  ┌─────────────┐   │
│  │  Isolate 1  │  │  Isolate 2  │   │
│  │  (Tenant A) │  │  (Tenant B) │   │
│  │  - Own heap │  │  - Own heap │   │
│  │  - 128MB    │  │  - 128MB    │   │
│  └─────────────┘  └─────────────┘   │
│         Shared V8 Engine            │
└─────────────────────────────────────┘
```

| Pros | Cons |
|------|------|
| ~0ms cold start | JavaScript only |
| Microsecond isolation | No direct syscall access |
| Used at massive scale | Limited compute time |
| Memory efficient | |

**P67 fit**: ❌ JavaScript only, can't run Python/LangGraph.

#### WebAssembly (Covered extensively above)
**P67 fit**: ❌ Native extension blocker makes LangGraph incompatible.

### 7. OS-Level Sandboxing

#### Seatbelt (macOS sandbox-exec)
**What**: macOS's built-in sandboxing mechanism.

| Pros | Cons |
|------|------|
| Native macOS integration | macOS only |
| No additional software | Limited to filesystem/network ACLs |
| Used by Cursor IDE | |

**P67 fit**: ❌ Not applicable to Linux servers.

#### Landlock (Linux 5.13+)
**What**: Unprivileged filesystem sandboxing in the Linux kernel.

| Pros | Cons |
|------|------|
| No root required | Linux 5.13+ only |
| Filesystem-level ACLs | Limited to filesystem |
| Stackable with other mechanisms | |

**P67 fit**: ⚠️ Could complement containers, not standalone solution.

### Recommendation Matrix

| Use Case | Recommended Solution | Why |
|----------|---------------------|-----|
| **Production (trusted code)** | Docker + hardening | Battle-tested, good ecosystem |
| **Production (untrusted code)** | gVisor or Kata + Firecracker | Stronger isolation boundaries |
| **Development** | Docker or Bubblewrap | Fast iteration |
| **High-frequency execution** | Container pool + gVisor | Warm starts + security |
| **Maximum security** | Firecracker microVM | Hardware isolation |

### Final Recommendation for P67

1. **Start with**: Docker + container pooling + hardened seccomp profile
2. **Upgrade to**: gVisor (`docker run --runtime=runsc`) if stronger isolation needed
3. **Consider**: Kata Containers + Firecracker if VM-level isolation required and KVM available

The key insight: **No alternative eliminates the need for process isolation**. Whether WASM, containers, or VMs, P67 workflows need:
- Resource limits
- Network restrictions  
- Filesystem isolation
- Timeout enforcement

Docker provides all of these with the best ecosystem support. Alternatives add security depth but not fundamentally different capabilities.

---

## References
- [Pyodide Documentation](https://pyodide.org/en/stable/)
- [Wazero GitHub](https://github.com/tetratelabs/wazero)
- [langchain-sandbox (archived)](https://github.com/langchain-ai/langchain-sandbox)
- [Arcjet: Wazero in Production](https://blog.arcjet.com/lessons-from-running-webassembly-in-production-with-go-wazero/)
- [Javy: JS to WASM](https://github.com/bytecodealliance/javy)
- [gVisor](https://gvisor.dev/) - User-space kernel for container sandboxing
- [Firecracker](https://firecracker-microvm.github.io/) - Lightweight microVMs
- [Kata Containers](https://katacontainers.io/) - OCI-compatible VM-based containers
- [Bubblewrap](https://github.com/containers/bubblewrap) - Unprivileged sandboxing
- [PEP 816 - WASI Support](https://peps.python.org/pep-0816/) - Official Python WASI support
- [Wasmer Python on Edge](https://wasmer.io/posts/python-on-the-edge-powered-by-webassembly) - Wasmer WASIX Python
- [componentize-py](https://github.com/bytecodealliance/componentize-py) - WASIp2 Python components
- [WASIp2 Guide](https://ideas.reify.ing/en/blog/complete-guide-to-wasip2-for-rust-python-programmers/) - Complete WASIp2 tutorial
