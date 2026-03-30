# Proposal A: One-Command Install Script

## Overview

A single shell script (`ops/install.sh`) that downloads the p67 CLI binary for the user's platform from a GitHub release and installs it to the local PATH. Optionally sets up the CoCo profile if `cortex` is detected.

## Phase 1 (Implemented)

### What it does

1. **Platform detection** -- Uses `uname -s` and `uname -m` to determine OS (Darwin/Linux) and architecture (arm64/x86_64), then maps to the correct archive name (e.g. `p67-darwin-arm64.tar.gz`).

2. **Version resolution** -- Defaults to "latest". Resolves the latest tag by following the GitHub `/releases/latest` redirect. Supports pinning with `--version <ver>`.

3. **Download and extract** -- Downloads the tarball from the GitHub release URL using `curl`, extracts with `tar`.

4. **macOS quarantine** -- Runs `xattr -cr` on the binary to clear the quarantine flag (unsigned binary).

5. **Install** -- Copies to `~/.local/bin/` by default, or `/usr/local/bin/` with `--global`. Creates the directory if needed.

6. **PATH check** -- Warns the user if the install directory isn't in PATH and prints shell-specific instructions.

7. **CoCo profile setup** -- If `cortex` CLI is detected and the session is interactive, prompts the user to set up the P67 CoCo profile via `cortex profile add p67 -c <connection>`.

### Usage

```bash
# One-liner (latest version)
curl -fsSL https://raw.githubusercontent.com/snowflake-eng/aura/main/p67/ops/install.sh | sh

# From a local clone
bash ops/install.sh

# Specific version, global install
bash ops/install.sh --global --version 0.5.0

# Custom download source
RELEASE_URL=https://my-mirror.example.com bash ops/install.sh
```

### Files changed

| File | Change |
|------|--------|
| `ops/install.sh` | New -- the installer script |
| `.github/workflows/p67-cli-release.yml` | Updated -- includes `install.sh` in release assets, adds quick-install section to release notes |
| `ops/bundle-user-package.sh` | Updated -- generated README includes "Alternative: Quick Install" section |

### Design decisions

- **POSIX `sh` compatible** -- Uses `#!/bin/sh` and avoids bashisms so it works when piped to `sh` on any system.
- **No dependencies beyond curl/tar** -- No Python, Node, or jq required.
- **Idempotent** -- Running twice just overwrites the binary. No side effects.
- **Non-interactive by default** -- When piped (`curl | sh`), skips all interactive prompts. Only prompts for CoCo profile setup when stdin is a TTY.
- **Configurable via env vars** -- `RELEASE_URL`, `INSTALL_DIR`, `VERSION` can all be overridden without flags.

## Phase 2 (Future)

- Add support for downloading from a Snowflake stage (for air-gapped / internal environments).
- Add checksum verification (SHA256) once we publish checksums alongside release assets.
- Add Windows support via a PowerShell install script.
- Consider auto-update mechanism (`p67 self-update`).
