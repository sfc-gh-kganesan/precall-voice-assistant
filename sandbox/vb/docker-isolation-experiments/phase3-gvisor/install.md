# gVisor Installation & Integration Guide

## What is gVisor?

gVisor is a user-space kernel written in Go that intercepts syscalls and handles them in a sandboxed process (Sentry), dramatically reducing the host kernel attack surface.

```
Standard Container:          gVisor Container:
┌──────────────────┐         ┌──────────────────┐
│  User Process    │         │  User Process    │
└────────┬─────────┘         └────────┬─────────┘
         │ syscalls                   │ syscalls
         ▼                            ▼
┌──────────────────┐         ┌──────────────────┐
│  Host Kernel     │         │  gVisor Sentry   │ ← User-space
│  (full attack    │         │  (~70 host calls)│
│   surface)       │         └────────┬─────────┘
└──────────────────┘                  │ minimal syscalls
                                      ▼
                             ┌──────────────────┐
                             │  Host Kernel     │
                             │  (reduced        │
                             │   attack surface)│
                             └──────────────────┘
```

## Installation

### macOS (Docker Desktop)
gVisor is not supported on Docker Desktop for Mac (no KVM).

### Linux (Ubuntu/Debian)
```bash
# Add gVisor repository
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg

curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null

# Install runsc
sudo apt-get update
sudo apt-get install -y runsc

# Configure Docker to use runsc
cat <<EOF | sudo tee /etc/docker/daemon.json
{
  "runtimes": {
    "runsc": {
      "path": "/usr/bin/runsc"
    }
  }
}
EOF

# Restart Docker
sudo systemctl restart docker

# Verify installation
docker run --runtime=runsc hello-world
```

### SPCS (Snowpark Container Services)
gVisor availability on SPCS needs to be verified with Snowflake platform team.

**Questions to answer:**
- [ ] Is runsc available as an OCI runtime?
- [ ] Can custom runtimes be specified?
- [ ] Are there alternative isolation mechanisms available?

## Usage

### Basic Usage
```bash
# Run container with gVisor
docker run --runtime=runsc -it python:3.11-slim python -c "print('Hello from gVisor')"
```

### With P67 Container Pool
```javascript
// In pool.js, add runtime option
const container = await docker.createContainer({
  Image: this.image,
  HostConfig: {
    Runtime: 'runsc',  // Use gVisor
    // ... other options
  },
});
```

## Platform Support (systrap mode)

gVisor's default `systrap` mode uses seccomp to intercept syscalls.

| Platform | Support |
|----------|---------|
| Linux x86_64 | ✅ Full |
| Linux ARM64 | ✅ Full |
| macOS | ❌ Not supported |
| Windows WSL2 | ⚠️ Limited |

## Performance Characteristics

| Workload Type | Overhead | Notes |
|---------------|----------|-------|
| CPU-bound | ~5-10% | Minimal syscall interception |
| I/O-bound | ~10-30% | Syscall overhead more visible |
| Network-bound | ~15-25% | Sentry handles network stack |
| Memory-heavy | ~5% | Similar to native |

## Known Limitations

1. **Unsupported syscalls**: Some rare syscalls not implemented
2. **No GPU passthrough**: CUDA/GPU workloads won't work
3. **File locking**: Some locking behaviors differ
4. **/proc differences**: Some /proc entries synthetic

## Compatibility Testing

Run this script to verify LangGraph works under gVisor:

```bash
#!/bin/bash
# test-gvisor-langgraph.sh

docker run --runtime=runsc --rm \
  -v $(pwd)/test_workflow.py:/app/test.py:ro \
  python:3.11-slim \
  sh -c "pip install langgraph==0.0.38 langchain-core && python /app/test.py"
```

## Benchmarking

```bash
cd ../phase1-pooling

# Benchmark with runc (default)
RUNTIME=runc node benchmark.js > ../benchmarks/results/runc.json

# Benchmark with runsc (gVisor)  
RUNTIME=runsc node benchmark.js > ../benchmarks/results/runsc.json

# Compare
node ../benchmarks/compare.js
```

## References

- [gVisor Documentation](https://gvisor.dev/docs/)
- [gVisor Security Model](https://gvisor.dev/docs/architecture_guide/security/)
- [runsc CLI Reference](https://gvisor.dev/docs/user_guide/quick_start/docker/)
- [gVisor Compatibility](https://gvisor.dev/docs/user_guide/compatibility/)
