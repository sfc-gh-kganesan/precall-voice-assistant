# Pattern-IQ Development Plan

A pattern catalog system where AI-powered skills extract, distill, and discover reusable **interaction patterns** across mixed-stack repos (Python, SQL, dbt, Streamlit, Cortex Agents, SPCS). Instead of indexing low-level objects (functions, classes), the system uses a multi-stage distillation pipeline to identify high-level "Recipes" — how 3-4 components interact to solve a specific problem. Patterns are stored in Snowflake with Cortex Search powering intent-based semantic discovery.

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   ARCHITECT          │     │   DISTILLER          │     │   LIBRARIAN          │
│                      │     │                      │     │                      │
│ Scan file tree       │────▶│ Extract "Recipes"    │────▶│ Generate synthetic   │
│ Group into domains   │     │ from high-utility     │     │ queries, reconcile   │
│ Score utility        │     │ code                  │     │ with existing, sync  │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
        │                            │                            │
        ▼                            ▼                            ▼
  /tmp/architect-            /tmp/pattern-              REUSABLE_PATTERNS table
  manifest.json              cards.json                 + Cortex Search
                                                        (insert/update/delete)
```

### Discovery Layer
```
┌─────────────────────────────────────────────────────┐
│   DISCOVER                                           │
│                                                      │
│ Cortex Code Skill "pattern-search"                   │
│ Streamlit app (future)                               │
│ Cortex Agent (future)                                │
│                                                      │
│ Intent-based search: matches engineer problems       │
│ against synthetic queries via Cortex Search           │
└─────────────────────────────────────────────────────┘
```

## Project Structure

```
pattern-iq/
├── pyproject.toml
├── PLAN.md
├── .cortex/
│   └── skills/
│       ├── pattern-extract/          # Orchestrator + all stages
│       │   ├── SKILL.md
│       │   ├── pyproject.toml
│       │   └── stages/
│       │       ├── architect/        # Stage 1: Contextual Scoping
│       │       │   ├── pyproject.toml
│       │       │   ├── references/
│       │       │   │   └── domains.md
│       │       │   └── scripts/
│       │       │       └── tree_scanner.py
│       │       ├── distiller/        # Stage 2: Pattern Extraction
│       │       │   ├── pyproject.toml
│       │       │   ├── references/
│       │       │   │   ├── categories.md
│       │       │   │   ├── frameworks.md
│       │       │   │   ├── schema.md
│       │       │   │   └── prompt-guide.md
│       │       │   └── scripts/
│       │       │       └── file_reader.py
│       │       └── librarian/        # Stage 3: Semantic Indexing + Reconciliation
│       │           ├── pyproject.toml
│       │           ├── references/
│       │           │   └── synthetic-queries-guide.md
│       │           └── scripts/
│       │               ├── insert_patterns.py
│       │               └── reconcile_patterns.py
│       └── pattern-search/           # Discovery
│           ├── SKILL.md
│           ├── pyproject.toml
│           └── scripts/
│               └── search.py
├── workflows/
│   └── pattern-iq.yml                # Template workflow for target repos
├── scripts/
│   └── upload_skills.sh
├── sql/
│   ├── setup.sql
│   └── teardown.sql
└── tests/
    ├── test_tree_scanner.py
    ├── test_file_reader.py
    ├── test_insert_patterns.py
    └── test_reconcile_patterns.py
```

---

## Phase 1 — Multi-Stage Distillation Pipeline

### Stage 1: Architect (Contextual Scoping)

**Input**: File tree, dependency files, README.md

**Action**: Groups files into Logical Domains (e.g., "Data Ingestion", "LLM Orchestration"), assigns Utility Scores (high/medium/low)

**Output**: `/tmp/architect-manifest.json` — JSON manifest tagging files with domains and utility scores

### Stage 2: Distiller (Pattern Extraction)

**Input**: High-utility code files from Stage 1

**Prompt Strategy**: Identify the core "Recipe" — how 3-4 components interact to solve a problem. Strip customer-specific names. Output a generic reusable template.

**Output**: `/tmp/pattern-cards.json` — Pattern Cards containing:
- Abstracted Code (clean-room template with `<PLACEHOLDER>`s)
- Dependency Graph (internal + external modules)
- Complexity Score (1-5)

### Stage 3: Librarian (Semantic Indexing + Reconciliation)

**Input**: Pattern Cards from Stage 2

**Action**:
1. Generates 5-10 Synthetic Queries per pattern — questions an engineer would ask when they have the problem this pattern solves
2. Reconciles fresh cards against existing patterns in Snowflake by querying `REUSABLE_PATTERNS` for the repo and semantically matching fresh cards to existing ones (by name and description, not exact string equality)
3. Syncs the catalog: inserts new patterns, updates matched patterns (preserving `PATTERN_ID`), deletes stale patterns that no longer emerge from extraction

**Output**: Rows synced in `PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS` with `SEARCH_CONTENT` built from pattern_name + description + usage_notes + synthetic_queries

### Discovery

Cortex Search service indexes `SEARCH_CONTENT`, matching engineer intent against synthetic queries. The `pattern-search` skill queries the service and displays Pattern Cards with "Why this matched" context.

---

## Phase 2 — Application Ecosystem (Future)

### Streamlit Discovery App
- Search bar powered by Cortex Search
- Browse/filter by category, language, framework, complexity
- Pattern detail view with syntax-highlighted abstracted code

### Cortex Agent
- Conversational discovery: "I need to build a Streamlit app with OAuth — what patterns do we have?"
- Can synthesize answers combining multiple patterns

### GitHub Actions Integration *(implemented)*

**Workflow template**: `workflows/pattern-iq.yml` — copied into each target repo's `.github/workflows/` directory. Manually triggered (`workflow_dispatch`).

**Inputs**:
- `target_path` (optional) — subdirectory for mono-repo scanning
- `connection` (optional, default `default`) — Snowflake connection name

**Skill Distribution**: Skills are packaged as a tarball and stored on `@PATTERN_IQ.PUBLIC.SKILLS_STAGE`. The CI workflow downloads and extracts them into the target repo's workspace before invoking Cortex Code. Upload new versions with `scripts/upload_skills.sh --connection <name>`.

**CI Mode**: The `PATTERN_IQ_CI=true` environment variable is set in the workflow. All stage SKILL.md files check this variable and skip mandatory approval stopping points, allowing the full Architect → Distiller → Librarian pipeline (including reconciliation) to run end-to-end without human interaction.

**Reconciliation**: On repeated runs, the Librarian reconciles freshly extracted patterns against existing ones in Snowflake. It semantically matches fresh cards to existing patterns (by name and description), then inserts new patterns, updates matched ones (preserving `PATTERN_ID`), and deletes stale ones that no longer emerge from extraction. This keeps the catalog in sync with the codebase without requiring incremental diff analysis.

**Authentication**: Uses the team CI service account (`AIFDE_CI_SVC`) with key-pair auth. See `sql/service_account.sql` for setup. The `PATTERN_IQ` role is granted to this user in `sql/setup.sql`.

**Required Repo Secrets**: `AIFDE_CI_SNOWFLAKE_ACCOUNT`, `AIFDE_CI_SNOWFLAKE_USER`, `AIFDE_CI_SNOWFLAKE_PRIVATE_KEY`

**Future enhancements**:
- Push-triggered re-extraction (uncomment push trigger in workflow template)
- Scheduled runs for periodic re-extraction

### Analytics
- Pattern coverage per repo, staleness detection
- "Request a pattern" workflow for gaps
