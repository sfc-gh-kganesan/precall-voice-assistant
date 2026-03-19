---
name: "create p67 cli skill"
created: "2026-03-18T16:52:23.906Z"
status: pending
---

# Plan: Create P67 CLI Skill for CoCo Profile Distribution

## Context

We need a **net-new CoCo skill** that teaches Cortex Code how to use the P67 CLI. This skill will be:

- Hosted on a **Snowflake stage** (`@CORTEX_CODE.CONFIG.P67_SKILLS/skills/p67-cli/`)
- Distributed via the **CoCo profile system** to `P67_USER_RL` users on Snowhouse
- Published using the `publish-coco-profile.sh` script we already drafted

The skill is distinct from the 4 existing project-scoped skills in `p67/.claude/skills/` (install, new-feature, sdk-sync, trigger-workflow) — those are for P67 _developers_. This new skill is for P67 _users_ who want CoCo to help them use the CLI.

## Skill Location

```
p67/skills/p67-cli/
  SKILL.md              # Main skill file (the deliverable)
  templates/            # Optional quick-reference patterns
    quickstart.md       # init -> build -> deploy -> run
```

Using `p67/skills/` (not `p67/.claude/skills/`) since this is for external distribution, not project-scoped usage.

## Task 1: Create the SKILL.md

File: `p67/skills/p67-cli/SKILL.md`

### Frontmatter

```
---
name: p67-cli
description: "Use the P67 CLI to build, deploy, and run agentic workflows on Snowflake. Use when: creating workflows, deploying to controld, managing secrets, setting up OAuth, viewing logs. Triggers: p67, workflow, deploy workflow, run workflow, p67 init, p67 build, p67 secret, p67 oauth, p67 connection, p67 logs."
tools:
  - bash
---
```

### Content Structure

The skill body will cover:

1. **Overview** — What P67 is (agentic workflow platform), what the CLI does

2. **Prerequisites** — Node.js 20+, Bun, connection to controld

3. **Command Reference** — All 10 command groups with syntax, options, and examples:
   - `p67 init` — Scaffold projects (TS or Python)
   - `p67 build` — Build to zip
   - `p67 workflow deploy/run/list/runs/versions/delete` — Full workflow lifecycle
   - `p67 connection add/list/remove/set-default` — Connection management
   - `p67 secret save/list/delete` — Secrets management
   - `p67 oauth connect/list/refresh/revoke` — OAuth flows
   - `p67 logs list` — View execution logs
   - `p67 manifest from-connection` — Bootstrap manifest from Snow CLI
   - `p67 coco setup` — Install CoCo commands for a project

4. **Common Workflows** — Step-by-step patterns:
   - First workflow (init -> build -> deploy -> run)
   - Adding secrets and parameters
   - Setting up OAuth for HTTP requests
   - Viewing run results and debugging failures

5. **Troubleshooting** — Common errors and fixes

6. **Stopping Points** — When to ask the user for input (connection name, workflow params, OAuth provider)

### Key design decisions

- The skill should be **self-contained** — a CoCo user with this skill loaded should be able to go from zero to a running workflow without needing other docs
- Derived from the CLI source in `p67/tools/p67-cli/src/commands/` and the existing `install` skill
- Command reference sourced from the actual Commander.js definitions (10 command groups, \~30 subcommands)
- Style follows the existing P67 skill conventions (markdown tables, code blocks, troubleshooting sections)

## Task 2: Add templates directory

File: `p67/skills/p67-cli/templates/quickstart.md`

A concise quickstart template the skill can reference for the most common happy-path:

```
p67 init myworkflow --language typescript
cd myworkflow
p67 build
p67 workflow deploy
p67 workflow run --name myworkflow
```

This keeps the main SKILL.md focused on reference while having a copy-pasteable template for the common case.

## Task 3: Update publish script

In `p67/scripts/publish-coco-profile.sh`, update:

```
SKILL_DIR="$(dirname "$0")/../skills/p67-cli"
```

This points to the new `p67/skills/p67-cli/` directory instead of the placeholder `p67/.claude/skills/p67-cli` path.

## Task 4: Test locally

1. Symlink or copy `p67/skills/p67-cli/` into `~/.snowflake/cortex/skills/p67-cli/`
2. Start a CoCo session
3. Verify with `/skill list` that `p67-cli` appears
4. Test trigger: `$p67-cli How do I deploy a workflow?`
5. Verify CoCo responds with correct `p67 build && p67 workflow deploy` instructions

## Dependency on existing scripts

This plan produces the skill content. Publishing and distribution use the scripts already drafted:

- `publish-coco-profile.sh` — uploads SKILL.md to stage, publishes profile
- `distribute-coco-profile.sh` — grants roles, prints onboarding instructions
