#!/bin/bash
#
# bundle-user-package.sh
#
# Assembles a self-contained user bundle for P67 onboarding.
# Output: dist/p67-user-bundle/ (and optionally a .tar.gz archive)
#
# Usage:
#   ./ops/bundle-user-package.sh [--archive]
#
#   --archive    Also create dist/p67-user-bundle.tar.gz
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE_DIR="${REPO_ROOT}/dist/p67-user-bundle"
ARCHIVE=false

for arg in "$@"; do
  case "$arg" in
    --archive) ARCHIVE=true ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

echo ""
echo "=========================================="
echo "    P67 User Bundle — Packaging"
echo "=========================================="
echo ""

# -------------------------------------------------------------------
# Clean and create bundle directory
# -------------------------------------------------------------------
rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}"/{docs/diagrams,examples}

# -------------------------------------------------------------------
# 1. Documentation
# -------------------------------------------------------------------
echo "Copying documentation..."

cp "${REPO_ROOT}/docs/ARCHITECTURE.md"       "${BUNDLE_DIR}/docs/architecture.md"
cp "${REPO_ROOT}/docs/snowflake-secrets-guide.md" "${BUNDLE_DIR}/docs/secrets-guide.md"
cp "${REPO_ROOT}/SLACK_instructions.md"      "${BUNDLE_DIR}/docs/slack-setup.md"

# CLI reference (from the CoCo skill — comprehensive command docs)
cp "${REPO_ROOT}/ops/coco-profile/skills/p67-cli/SKILL.md" \
   "${BUNDLE_DIR}/docs/cli-reference.md"

# CLI quick-reference cheat sheet
cp "${REPO_ROOT}/ops/coco-profile/skills/p67-cli/templates/quickstart.md" \
   "${BUNDLE_DIR}/docs/cli-quickstart.md"

# Architecture diagrams (SVG for rendering, MMD for editing)
cp "${REPO_ROOT}/docs/diagrams/"*.svg "${BUNDLE_DIR}/docs/diagrams/"
cp "${REPO_ROOT}/docs/diagrams/"*.mmd "${BUNDLE_DIR}/docs/diagrams/"

# -------------------------------------------------------------------
# 2. CoCo profile setup script
# -------------------------------------------------------------------
echo "Copying setup script..."

cp "${REPO_ROOT}/ops/coco-profile/setup.sh" "${BUNDLE_DIR}/setup.sh"
chmod +x "${BUNDLE_DIR}/setup.sh"

# -------------------------------------------------------------------
# 3. Example workflows (sanitized)
# -------------------------------------------------------------------
echo "Copying example workflows..."

# hello-world (from number_one)
mkdir -p "${BUNDLE_DIR}/examples/hello-world/src"
cp "${REPO_ROOT}/example_workflows/number_one/src/index.ts"   "${BUNDLE_DIR}/examples/hello-world/src/"
cp "${REPO_ROOT}/example_workflows/number_one/manifest.yaml"  "${BUNDLE_DIR}/examples/hello-world/"
cp "${REPO_ROOT}/example_workflows/number_one/build.js"       "${BUNDLE_DIR}/examples/hello-world/"
cp "${REPO_ROOT}/example_workflows/number_one/package.json"   "${BUNDLE_DIR}/examples/hello-world/"
cp "${REPO_ROOT}/example_workflows/number_one/tsconfig.json"  "${BUNDLE_DIR}/examples/hello-world/"
cp "${REPO_ROOT}/example_workflows/number_one/README.md"      "${BUNDLE_DIR}/examples/hello-world/"
if [ -f "${REPO_ROOT}/example_workflows/number_one/Makefile" ]; then
  cp "${REPO_ROOT}/example_workflows/number_one/Makefile"     "${BUNDLE_DIR}/examples/hello-world/"
fi

# human-in-the-loop (from with_interrupt)
mkdir -p "${BUNDLE_DIR}/examples/human-in-the-loop/src"
cp "${REPO_ROOT}/example_workflows/with_interrupt/src/index.ts"  "${BUNDLE_DIR}/examples/human-in-the-loop/src/"
cp "${REPO_ROOT}/example_workflows/with_interrupt/manifest.yaml" "${BUNDLE_DIR}/examples/human-in-the-loop/"
cp "${REPO_ROOT}/example_workflows/with_interrupt/build.js"      "${BUNDLE_DIR}/examples/human-in-the-loop/"
cp "${REPO_ROOT}/example_workflows/with_interrupt/package.json"  "${BUNDLE_DIR}/examples/human-in-the-loop/"
cp "${REPO_ROOT}/example_workflows/with_interrupt/tsconfig.json" "${BUNDLE_DIR}/examples/human-in-the-loop/"

# workflow-editor-template (from template)
if [ -d "${REPO_ROOT}/example_workflows/template" ]; then
  mkdir -p "${BUNDLE_DIR}/examples/workflow-editor-template/conf"
  cp "${REPO_ROOT}/example_workflows/template/workflow_spec.json"  "${BUNDLE_DIR}/examples/workflow-editor-template/" 2>/dev/null || true
  cp "${REPO_ROOT}/example_workflows/template/AGENTS.md"           "${BUNDLE_DIR}/examples/workflow-editor-template/" 2>/dev/null || true
  cp "${REPO_ROOT}/example_workflows/template/LEARN_WORKFLOW.md"   "${BUNDLE_DIR}/examples/workflow-editor-template/" 2>/dev/null || true
  cp "${REPO_ROOT}/example_workflows/template/conf/"*              "${BUNDLE_DIR}/examples/workflow-editor-template/conf/" 2>/dev/null || true
fi

# -------------------------------------------------------------------
# 4. Sanitize hardcoded values in examples
# -------------------------------------------------------------------
echo "Sanitizing hardcoded values..."

# Remove any p67.yml files with hardcoded endpoints (users should use p67 connection add)
find "${BUNDLE_DIR}/examples" -name "p67.yml" -exec rm -f {} \;

# -------------------------------------------------------------------
# 5. Generate the bundle README
# -------------------------------------------------------------------
echo "Generating README..."

cat > "${BUNDLE_DIR}/README.md" << 'READMEEOF'
# P67 (Cortex Mesh) — User Guide

P67 is a platform for building, deploying, and running **agentic workflows** on Snowflake. You write workflow code in TypeScript or Python, deploy it to a control plane service, and execute it on Snowflake SPCS. Workflows get a rich SDK with Snowflake SQL, Cortex AI, OAuth, HTTP, email, and human-in-the-loop capabilities.

---

## Getting Started

### 1. Get Access

Request the **`P67_USER_RL`** role via a Lift ticket (or ask a SECURITYADMIN). This role grants access to the deployed P67 app and the CoCo profile.

### 2. Install the CoCo Profile

The P67 CoCo profile teaches Cortex Code how to use the P67 CLI. Once installed, CoCo can scaffold, build, deploy, and run workflows on your behalf.

```bash
# Run the setup script (creates a Snowhouse connection + installs the profile)
./setup.sh

# Or do it manually:
cortex profile add p67 -c snowhouse
cortex profile set-default p67
```

Verify:
```bash
cortex -c snowhouse
# Inside CoCo: /skill list
# You should see "p67-cli"
```

> **Note**: Profiles work in CoCo Desktop and CoCo CLI only (not Snowsight).

To update later: `cortex profile sync p67 -c snowhouse`

### 3. Connect to controld

Get the controld endpoint URL from your admin, or:

```sql
CALL p67.v1.app_url();
```

Then register it:

```bash
p67 connection add prod --endpoint <url> --set-default
# You'll be prompted for a Snowflake PAT
```

### 4. Create Your First Workflow

**With CoCo** (recommended):
```
> Create a P67 workflow that queries Snowflake for the current timestamp and returns it
```

CoCo will handle `p67 init`, code editing, `p67 build`, `p67 workflow deploy`, and `p67 workflow run`.

**Manually:**
```bash
p67 init my-workflow
cd my-workflow
p67 manifest from-connection    # Bootstrap Snowflake config
# Edit src/index.ts or src/main.py
p67 build
p67 workflow deploy
p67 workflow run --name my-workflow
```

---

## What's in This Bundle

### Documentation (`docs/`)

| File | Description |
|------|-------------|
| [architecture.md](docs/architecture.md) | Full system architecture with diagrams — components, data model, deployment topology, IPC protocol |
| [cli-reference.md](docs/cli-reference.md) | Complete P67 CLI command reference with all flags and options |
| [cli-quickstart.md](docs/cli-quickstart.md) | Quick-reference cheat sheet for common CLI patterns |
| [secrets-guide.md](docs/secrets-guide.md) | Guide for using Snowflake SECRET objects with P67 workflows |
| [slack-setup.md](docs/slack-setup.md) | Slack bot integration setup instructions |

### Examples (`examples/`)

| Directory | Description |
|-----------|-------------|
| [hello-world/](examples/hello-world/) | Basic 3-node LangGraph workflow (TypeScript). Good starting point. |
| [human-in-the-loop/](examples/human-in-the-loop/) | Workflow that pauses for human approval via `sdk.interrupt()`. |
| [workflow-editor-template/](examples/workflow-editor-template/) | Invoice processing workflow spec + JSON schema for the workflow editor. |

### CoCo Profile

The CoCo profile (installed via `setup.sh`) gives Cortex Code the **p67-cli** skill, which includes:

- Full CLI command reference for all `p67` commands
- Workflow authoring guidance (define, generate, implement)
- Common workflow patterns and troubleshooting
- Safety guardrails (CoCo asks before deploying, deleting, or saving secrets)

---

## Prerequisites

- **`P67_USER_RL`** role granted on your Snowflake account
- **Cortex Code** (Desktop app or CLI) — [install docs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-code)
- **Node.js** v20+ and **Bun** v1.1+ (for the `p67` CLI)
- A **Snowflake PAT** (Personal Access Token) for CLI authentication

---

## Quick Reference

```bash
# Scaffold a new workflow
p67 init my-workflow --language typescript

# Build and deploy
p67 build
p67 workflow deploy

# Run (with parameters)
p67 workflow run --name my-workflow -p KEY=value

# Check run history
p67 workflow runs --name my-workflow

# View logs
p67 logs list --run <runId>

# Manage secrets
echo "my-key" | p67 secret save MY_SECRET

# Set up OAuth
p67 oauth connect github --secret-name GITHUB_TOKEN --client-id <id> --client-secret <secret>
```
READMEEOF

# -------------------------------------------------------------------
# 7. Summary
# -------------------------------------------------------------------
echo ""
echo "=========================================="
echo "    Bundle complete!"
echo "=========================================="
echo ""

FILE_COUNT=$(find "${BUNDLE_DIR}" -type f | wc -l | tr -d ' ')
echo "  Location: ${BUNDLE_DIR}"
echo "  Files:    ${FILE_COUNT}"
echo ""
echo "  docs/          — Architecture, quickstart, CLI reference, secrets guide, Slack setup"
echo "  examples/      — hello-world, human-in-the-loop, workflow-editor-template"
echo "  setup.sh       — CoCo profile onboarding (run this first)"
echo "  README.md      — Start here"
echo ""

# -------------------------------------------------------------------
# 8. Optional: create archive
# -------------------------------------------------------------------
if [ "${ARCHIVE}" = true ]; then
  echo "Creating archive..."
  ARCHIVE_PATH="${REPO_ROOT}/dist/p67-user-bundle.tar.gz"
  tar -czf "${ARCHIVE_PATH}" -C "${REPO_ROOT}/dist" "p67-user-bundle"
  ARCHIVE_SIZE=$(du -h "${ARCHIVE_PATH}" | cut -f1)
  echo "  Archive: ${ARCHIVE_PATH} (${ARCHIVE_SIZE})"
  echo ""
fi

echo "Done."
