# P67 Container Security Audit Checklist

## Pre-Deployment Checklist

### 1. Capability Management
- [ ] `CAP_DROP=ALL` - Drop all Linux capabilities
- [ ] Only add back capabilities that are absolutely required
- [ ] Document any capabilities that must be retained and why

### 2. Filesystem Security
- [ ] `--read-only` root filesystem enabled
- [ ] `/tmp` mounted as tmpfs with `noexec,nosuid`
- [ ] Workflow directory mounted read-only where possible
- [ ] No sensitive host paths mounted into container

### 3. Privilege Escalation Prevention
- [ ] `--security-opt=no-new-privileges:true` set
- [ ] No setuid binaries in container image
- [ ] User namespace enabled (non-root user inside container)

### 4. Resource Limits
- [ ] Memory limit set (`--memory`)
- [ ] CPU limit set (`--cpus` or `--cpu-period/quota`)
- [ ] PID limit set (`--pids-limit`)
- [ ] Ulimits configured (`--ulimit`)

### 5. Network Isolation
- [ ] `--network=none` for workflows that don't need network
- [ ] Or custom network with egress rules if network required
- [ ] No `--net=host`

### 6. Seccomp Profile
- [ ] Custom seccomp profile applied
- [ ] Profile tested with target workload
- [ ] Blocked syscalls documented:
  - `mount`, `umount` - filesystem manipulation
  - `ptrace` - process debugging/injection
  - `reboot` - system control
  - `swapon`, `swapoff` - memory manipulation
  - `init_module`, `delete_module` - kernel modules
  - `acct` - process accounting
  - `settimeofday` - time manipulation
  - `sethostname`, `setdomainname` - identity manipulation

### 7. Image Security
- [ ] Base image from trusted source
- [ ] Image scanned for vulnerabilities (Trivy, Snyk, etc.)
- [ ] No unnecessary packages installed
- [ ] Image pinned to specific digest (not just tag)

### 8. Runtime Monitoring
- [ ] Container logs captured
- [ ] Resource usage monitored
- [ ] Execution timeouts enforced
- [ ] Anomaly detection for syscall patterns

---

## Security Levels

### Level 1: Standard (Current P67)
```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
network_mode: bridge  # or custom
```

### Level 2: Hardened
```yaml
security_opt:
  - no-new-privileges:true
  - seccomp:seccomp-profile.json
cap_drop:
  - ALL
read_only: true
network_mode: none
tmpfs:
  /tmp: rw,noexec,nosuid,size=64m
```

### Level 3: Maximum (gVisor)
```yaml
runtime: runsc
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
read_only: true
network_mode: none
```

---

## Known Attack Vectors

| Vector | Mitigation | Status |
|--------|------------|--------|
| Kernel exploit via syscall | Seccomp + gVisor | ⚠️ Partial |
| Container escape via mount | CAP_DROP + read-only | ✅ |
| Privilege escalation | no-new-privileges | ✅ |
| Resource exhaustion | Memory/CPU limits | ✅ |
| Network exfiltration | network=none | ✅ |
| Time-based attacks | settimeofday blocked | ✅ |

---

## Testing Procedure

1. **Functional test**: Verify LangGraph workflow runs successfully
2. **Security test**: Attempt blocked operations:
   ```bash
   # Should fail
   docker exec <container> mount /dev/sda1 /mnt
   docker exec <container> ptrace attach 1
   docker exec <container> reboot
   ```
3. **Resource test**: Verify limits are enforced
4. **Performance test**: Measure overhead vs unhardened
