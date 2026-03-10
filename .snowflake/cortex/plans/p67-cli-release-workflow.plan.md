---
name: "p67 cli release workflow"
created: "2026-03-10T20:59:03.111Z"
status: pending
---

# Plan: p67 CLI Release Workflow

## Context

The p67 CLI (`@p67/cli`) at `p67/tools/p67-cli/` is built with Bun's `--compile` flag, producing a single self-contained binary. Currently there is no release/distribution mechanism -- only a local `make install` that symlinks the binary.

We will model the release workflow after the CoCo Desktop workflow, adapted for a Bun CLI binary instead of an Electron app.

## Architecture

```
flowchart TD
    Dev["Developer runs prep-release.sh"] --> Branch["Creates release-p67-cli-X.Y.Z branch"]
    Branch --> Push["Pushes to GitHub"]
    Push --> Trigger["Manually trigger workflow on release branch"]
    Trigger --> Validate["Validate release branch name"]
    Validate --> Matrix["Matrix build: 5 platforms"]
    Matrix --> MacArm["macOS arm64"]
    Matrix --> MacX64["macOS x64"]
    Matrix --> LinuxX64["Linux x64"]
    Matrix --> LinuxArm["Linux arm64"]
    Matrix --> WinX64["Windows x64"]
    MacArm --> Artifacts["Upload artifacts"]
    MacX64 --> Artifacts
    LinuxX64 --> Artifacts
    LinuxArm --> Artifacts
    WinX64 --> Artifacts
    Artifacts --> Release["Create draft GitHub Release"]
```

## File Changes

### 1. Create `p67/tools/p67-cli/scripts/prep-release.sh`

A shell script developers run locally to prepare a release:

```
#!/usr/bin/env bash
# Usage: ./scripts/prep-release.sh [patch|minor|major]
```

Steps:

- Accept a semver bump type argument (default: `patch`)
- Read current version from `package.json`
- Bump the version using `node -e` (no external deps)
- Create branch `release-p67-cli-X.Y.Z`
- Commit the version bump
- Push the branch to origin
- Print instructions to trigger the workflow

### 2. Create `.github/workflows/p67-cli-release.yml`

Workflow name: **"p67 CLI - New Release"**

```
on:
  workflow_dispatch:
    inputs:
      release_type:
        description: "Release type"
        required: true
        type: choice
        options: [dev, beta, prod]
        default: "dev"
```

#### Jobs

**Job 1: `check-valid-release-branch`**

- Validates current branch matches `release-p67-cli-*`
- Identical pattern to CoCo's branch check

**Job 2: `build` (matrix strategy)**

Matrix targets (all cross-compiled from a single runner type where possible, but we use native runners for best compatibility):

| Platform    | Bun target         | Runner                      | Artifact name      |
| ----------- | ------------------ | --------------------------- | ------------------ |
| macOS arm64 | `bun-darwin-arm64` | `macos-15-xlarge`           | `p67-darwin-arm64` |
| macOS x64   | `bun-darwin-x64`   | `macos-15-large`            | `p67-darwin-x64`   |
| Linux x64   | `bun-linux-x64`    | `ubuntu-latest`             | `p67-linux-x64`    |
| Linux arm64 | `bun-linux-arm64`  | `ubuntu-latest-64cores-arm` | `p67-linux-arm64`  |
| Windows x64 | `bun-windows-x64`  | `windows-latest`            | `p67-windows-x64`  |

Each build job:

1. Checkout
2. Setup Node.js (from `.nvmrc`) + pnpm + Bun
3. Install dependencies: `pnpm install --filter "@p67/workflow-sdk" --filter "@p67/cli"`
4. Build workflow-sdk first: `pnpm --filter "@p67/workflow-sdk" run build`
5. Cross-compile CLI: `cd p67/tools/p67-cli && bun build ./src/index.ts --compile --target=<bun-target> --outfile ./bin/p67`
6. (Placeholder) Code signing step (commented out)
7. Create platform-specific archive (`.tar.gz` for macOS/Linux, `.zip` for Windows)
8. Upload artifact

**Job 3: `create-github-release`**

- Needs all build jobs
- Downloads all artifacts
- Determines version from package.json + release\_type suffix
- Creates git tag `p67-cli-vX.Y.Z[-dev|-beta]`
- Creates draft GitHub Release with all platform archives
- Includes `latest.txt` with the version string
- Release body includes post-download usage instructions

#### Signing Placeholders

Each build job will have commented-out steps:

```
# --- Code Signing (not yet configured) ---
# - name: Sign binary (macOS)
#   if: contains(matrix.platform, 'darwin')
#   run: |
#     # codesign --sign "${{ secrets.MACOS_CERTIFICATE_ID }}" ./bin/p67
#     # xcrun notarytool submit ...
#   env:
#     MACOS_CERTIFICATE: ${{ secrets.MACOS_CERTIFICATE }}
#     ...
```

### 3. Add usage instructions to release notes template

The `create-github-release` job will include a release body with per-platform instructions:

**macOS**:

```
# Remove quarantine attribute (required for unsigned binaries)
xattr -cr ./p67
chmod +x ./p67
./p67 --version
```

**Linux**:

```
chmod +x ./p67
./p67 --version
```

**Windows**:

```
# If SmartScreen blocks it, right-click -> Properties -> Unblock
.\p67.exe --version
```

### 4. Environment and Secrets Required

The workflow needs:

- `GITHUB_TOKEN` (default or PAT for release creation)
- No signing secrets initially (placeholders only)

Future secrets (documented as comments):

- `MACOS_CERTIFICATE`, `MACOS_CERTIFICATE_PWD`, `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_SPECIFIC_PASSWORD`
- `WINDOWS_CODE_SIGN_*` secrets

## Key Differences from CoCo Desktop Workflow

| Aspect              | CoCo Desktop              | p67 CLI                |
| ------------------- | ------------------------- | ---------------------- |
| Build tool          | npm + Electron            | Bun `--compile`        |
| Signing             | Full macOS + Windows      | Placeholders only      |
| SSH Server          | Yes (separate job)        | No                     |
| Windows signing job | Separate sign-windows job | N/A                    |
| Artifact types      | DMG, ZIP, EXE installers  | Single binary archives |
| Branch pattern      | `release-desktop-*`       | `release-p67-cli-*`    |
| Release tag pattern | `desktop-release-X.Y.Z`   | `p67-cli-vX.Y.Z`       |

## Files to Create

1. `p67/tools/p67-cli/scripts/prep-release.sh` - Release preparation script
2. `.github/workflows/p67-cli-release.yml` - GitHub Actions workflow
