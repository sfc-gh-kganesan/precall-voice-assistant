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

## Prerequisites

- `uv` installed (`uv --version`)
- Snowflake connection with access to `PATTERN_IQ` database

### Snowflake Object Setup

Before running the pipeline, ensure the required Snowflake objects exist. Run each statement from `<PROJECT_ROOT>/sql/setup.sql` via `snowflake_sql_execute`. The statements are idempotent (`IF NOT EXISTS` / `OR REPLACE`):

1. `CREATE DATABASE IF NOT EXISTS PATTERN_IQ`
2. `CREATE TABLE IF NOT EXISTS PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS (...)` — see `sql/setup.sql` for full schema
3. `CREATE OR REPLACE CORTEX SEARCH SERVICE PATTERN_IQ.PUBLIC.PATTERN_SEARCH_SVC (...)` — see `sql/setup.sql` for full definition

`<PROJECT_ROOT>` is the root of the **pattern-iq** project (parent of `.cortex/`), NOT the target repository being scanned.

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
