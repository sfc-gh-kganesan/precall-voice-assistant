# p67 CLI tool

## Prerequisites

Install the [`bun`](https://bun.com/) runtime:

```
curl -fsSL https://bun.sh/install | bash
```

## Installation

Run `make clean install` to rebuild and install the CLI binary.

## Releasing

### Prerequisites

Install the linting tools used to validate release scripts and workflows:

```bash
brew install shellcheck actionlint
```

### Linting

Before pushing changes to the release workflow or scripts, run:

```bash
# Validate the GitHub Actions workflow
actionlint ../../.github/workflows/p67-cli-release.yml

# Validate the release script
shellcheck scripts/prep-release.sh
```

### Creating a release

1. **Prepare the release branch.** From the repo root on your working branch, run:

   ```bash
   cd p67/tools/p67-cli
   ./scripts/prep-release.sh [patch|minor|major]
   ```

   This bumps the version in `package.json`, creates a `release-p67-cli-<version>` branch, commits the change, and pushes it to origin.

2. **Trigger the workflow.** Go to [GitHub Actions](../../actions/workflows/p67-cli-release.yml), select the **p67 CLI - New Release** workflow, click **Run workflow**, choose the `release-p67-cli-*` branch, and pick a release type (`dev`, `beta`, or `prod`).

3. **Review the draft release.** The workflow builds binaries for all platforms (macOS arm64/x64, Linux x64/arm64, Windows x64), uploads them as artifacts, and creates a **draft** GitHub Release. Review the draft, then publish it when ready.

4. **Merge back.** Open a PR to merge the release branch into your main branch.

### Supported platforms

| Platform | Archive |
|---|---|
| macOS arm64 | `p67-darwin-arm64.tar.gz` |
| macOS x64 | `p67-darwin-x64.tar.gz` |
| Linux x64 | `p67-linux-x64.tar.gz` |
| Linux arm64 | `p67-linux-arm64.tar.gz` |
| Windows x64 | `p67-windows-x64.zip` |

### Post-download setup (unsigned binaries)

**macOS** — remove the quarantine attribute:

```bash
tar -xzf p67-darwin-*.tar.gz
xattr -cr ./p67
chmod +x ./p67
```

**Linux**:

```bash
tar -xzf p67-linux-*.tar.gz
chmod +x ./p67
```

**Windows** — if SmartScreen blocks the executable, right-click `p67.exe` > Properties > Unblock.
