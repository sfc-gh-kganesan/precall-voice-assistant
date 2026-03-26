# Proposal C+D: SessionStart Health Check Hook & Global Workflow Commands

## Overview

Two additions to the P67 CoCo profile that improve the onboarding experience and make workflow authoring commands available to all profile users.

## Part C: SessionStart Health Check Hook

### What

A bash script (`ops/coco-profile/scripts/p67-health-check.sh`) runs automatically at the start of every CoCo session via a profile hook. It performs three checks:

1. **p67 in PATH** — If the CLI is not installed, prints an install hint.
2. **At least one connection** — Parses `p67 connection list` output. If no connections exist, prints a setup hint.
3. **Default endpoint reachable** — If a default connection is set, probes `<endpoint>/api/health` with a 5-second curl timeout. Reports whether controld is reachable.

### Design decisions

- The script always exits 0 so it never blocks session startup.
- The 10-second hook timeout (set in profile.json) gives enough headroom for the curl probe plus CLI startup.
- Output is prefixed with `[P67]` for easy identification in CoCo session logs.
- Parses `p67 connection list` text output: default connections are marked with `* <name>`, endpoint on the next line as `Endpoint: <url>`.

### Files changed

| File | Change |
|------|--------|
| `ops/coco-profile/scripts/p67-health-check.sh` | New — health check script |
| `ops/coco-profile/profile.json` | Added `hooks` array with SessionStart entry |
| `ops/coco-profile/publish.sh` | Added Step 2c to upload `scripts/` to stage |

## Part D: Global Workflow Commands

### What

Three workflow authoring commands (previously local to the `coco/commands/` dev directory) are now distributed via the CoCo profile so any user with the P67 profile gets them automatically.

| Command | Purpose |
|---------|---------|
| `/define-workflow` | Interactive workflow spec builder — guides users through requirements gathering and generates `workflow_spec.json` |
| `/generate-workflow` | Implements workflow code in a pre-generated P67 project from a workflow spec |
| `/generate-workflow-code` | Modifies and implements workflow code with Cortex Agent/Analyst integration |

### How

- Command `.md` files are copied to `ops/coco-profile/commands/` (identical to `coco/commands/` originals).
- `profile.json` declares a `commandRepos` entry pointing to `@P67.COCO_SKILLS.P67_CLI/commands/` on the Snowflake stage.
- `publish.sh` uploads the commands directory to the stage (Step 2b).

### Files changed

| File | Change |
|------|--------|
| `ops/coco-profile/commands/define-workflow.md` | New — copied from `coco/commands/` |
| `ops/coco-profile/commands/generate-workflow.md` | New — copied from `coco/commands/` |
| `ops/coco-profile/commands/generate-workflow-code.md` | New — copied from `coco/commands/` |
| `ops/coco-profile/profile.json` | Added `commandRepos` entry |
| `ops/coco-profile/publish.sh` | Added Step 2b to upload `commands/` to stage |

## Stage layout after publish

```
@P67.COCO_SKILLS.P67_CLI/
├── skills/
│   └── p67-cli/
│       ├── SKILL.md
│       ├── templates/
│       └── references/
├── commands/
│   ├── define-workflow.md
│   ├── generate-workflow.md
│   └── generate-workflow-code.md
└── scripts/
    └── p67-health-check.sh
```

## Testing

1. `bash ops/coco-profile/scripts/p67-health-check.sh` — verify output for each scenario (no p67, no connections, unreachable endpoint, success).
2. `python3 -c "import json; json.load(open('ops/coco-profile/profile.json'))"` — verify valid JSON.
3. `diff coco/commands/*.md ops/coco-profile/commands/` — verify command files are identical copies.
