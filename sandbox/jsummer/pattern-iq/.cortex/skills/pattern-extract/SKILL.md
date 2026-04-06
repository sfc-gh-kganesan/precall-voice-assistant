---
name: pattern-extract
description: >
  Extract reusable code patterns from a repository and catalog them in Snowflake.
  Use when: scanning a project for patterns, cataloging code snippets, populating
  the pattern library, "extract patterns", "scan for patterns", "catalog this repo",
  "find patterns in", "index this codebase".
---

# Pattern Extract (Orchestrator)

End-to-end pipeline that chains three stages: **Architect** → **Distiller** → **Librarian**.

## CI Mode

If the environment variable `PATTERN_IQ_CI` is set to `true`, this pipeline is running in headless CI mode. In CI mode:
- **Skip all mandatory stopping points** — do NOT use `AskUserQuestion` for approval gates
- Auto-approve each stage output and proceed directly to the next phase
- Continue through the full pipeline (Architect → Distiller → Librarian) without pausing
- **Do NOT re-read source files** — the `file_reader.py` script in Phase 2 loads all necessary content. Do not use the `read` tool on target repository files during Phase 2.
- **Extract patterns inline** — in Phase 2, extract patterns directly in the main agent context from `distiller-input.json`. Do NOT use subagents — they cannot write files in headless mode. See Distiller SKILL.md "CI Mode" section.

> **Note**: For large repos (10+ high-utility domains), CI inline extraction may be slow or hit context limits. Prefer running locally in interactive mode, which uses parallel background subagents for better performance.

## Prerequisites

- `uv` installed (`uv --version`)
- Snowflake connection with access to `PATTERN_IQ` database

### Snowflake Object Verification

Before running the pipeline, verify the required Snowflake objects exist. Do NOT attempt to create them — the CI role may lack DDL privileges.

1. `SHOW DATABASES LIKE 'PATTERN_IQ'` — if 0 rows, **STOP** immediately: "ERROR: PATTERN_IQ database does not exist. A privileged role must run sql/setup.sql first."
2. `DESCRIBE TABLE PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS` — if error, **STOP** immediately: "ERROR: REUSABLE_PATTERNS table does not exist or is inaccessible. A privileged role must run sql/setup.sql first."

## Pipeline

**IMPORTANT**: Each stage SKILL.md uses `<SKILL_DIRECTORY>` to refer to **its own stage directory**, not the orchestrator directory. When executing a stage, resolve `<SKILL_DIRECTORY>` as follows:

- Architect: `<SKILL_DIRECTORY>` = `<ORCHESTRATOR_DIR>/stages/architect`
- Distiller: `<SKILL_DIRECTORY>` = `<ORCHESTRATOR_DIR>/stages/distiller`
- Librarian: `<SKILL_DIRECTORY>` = `<ORCHESTRATOR_DIR>/stages/librarian`

Where `<ORCHESTRATOR_DIR>` is the directory containing this file (the pattern-extract skill root).

### Phase 1: Architect (Contextual Scoping)

Load and execute `<ORCHESTRATOR_DIR>/stages/architect/SKILL.md`.

- **Input**: `repo_path` (from user)
- **Output**: `/tmp/architect-manifest.json`, `project_root`
- **MANDATORY STOPPING POINT**: User approves domain groupings and utility scores.

### Phase 2: Distiller (Pattern Extraction)

Load and execute `<ORCHESTRATOR_DIR>/stages/distiller/SKILL.md`.

- **Input**: `/tmp/architect-manifest.json`, `project_root`
- **Output**: `/tmp/pattern-cards.json` (each card contains `repo_name`, `source_repo_link`, and all pattern metadata)
- **MANDATORY STOPPING POINT**: User approves Pattern Cards.

### Phase 3: Librarian (Semantic Indexing + Reconciliation)

Load and execute `<ORCHESTRATOR_DIR>/stages/librarian/SKILL.md`.

- **Input**: `/tmp/pattern-cards.json`, `connection_name`
- **Output**: Rows synced in `PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS` (inserts, updates, and deletes)
- **MANDATORY STOPPING POINT**: User approves synthetic queries, then approves the reconciliation plan.

The Librarian now includes a **reconciliation step**: before writing to Snowflake, it queries existing patterns for the repo, semantically matches fresh cards against them (by name and description, not exact string equality), and determines what to insert (new patterns), update (existing patterns that were re-extracted), or delete (stale patterns that no longer emerge from extraction). This ensures the catalog stays in sync with the codebase across repeated runs.

## Stopping Points

- After Phase 1: user approves manifest
- After Phase 2: user approves Pattern Cards
- After Phase 3 (pre-insert): user approves synthetic queries
- After Phase 3 (pre-sync): user approves reconciliation plan (matches, new patterns, stale deletions)

## Output

Rows synced in `PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS`. Verify with:
```sql
SELECT PATTERN_ID, PATTERN_NAME, CATEGORY, COMPLEXITY_SCORE, SOURCE_REPO_LINK, UPDATED_AT
FROM PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS
WHERE REPO_NAME = '<repo_name>' ORDER BY UPDATED_AT DESC;
```
