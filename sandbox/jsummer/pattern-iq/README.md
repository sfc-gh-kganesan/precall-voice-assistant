# Pattern-IQ

A pattern catalog system that uses AI-powered Cortex Code skills to extract, distill, and discover reusable **interaction patterns** across mixed-stack repositories (Python, SQL, dbt, Streamlit, Cortex Agents, SPCS).

Instead of indexing low-level objects like functions or classes, Pattern-IQ uses a multi-stage distillation pipeline to identify high-level "Recipes" — how 3-4 components interact to solve a specific problem. Patterns are stored in Snowflake with Cortex Search powering intent-based semantic discovery.

## How It Works

The system has two Cortex Code skills: **pattern-extract** (writes to the catalog) and **pattern-search** (reads from the catalog).

### Extraction Pipeline

The `pattern-extract` skill chains three stages:

```
Architect              Distiller              Librarian
Scan file tree    -->  Extract "Recipes"  --> Generate synthetic
Group into domains     from high-utility      queries + store in
Score utility          code                   Snowflake
```

**Stage 1 — Architect**: Scans the repository file tree, groups files into logical domains (e.g., "Data Ingestion", "LLM Orchestration"), and assigns utility scores (high/medium/low). Uses `scripts/tree_scanner.py` to collect file metadata, then the LLM performs domain classification.

**Stage 2 — Distiller**: Reads high-utility files (up to 60K characters per domain) and extracts interaction patterns. Each pattern becomes a "Pattern Card" with abstracted code (generic templates with `<PLACEHOLDER>` tokens), a dependency graph, complexity score, and usage notes. The LLM identifies how components interact rather than cataloging individual functions.

**Stage 3 — Librarian**: Generates 5-10 synthetic search queries per pattern — questions an engineer would ask when they have the problem the pattern solves. Builds a `SEARCH_CONTENT` field from the pattern name, description, usage notes, and synthetic queries. Before writing to Snowflake, the Librarian **reconciles** fresh cards against existing patterns for the repo: it queries the catalog, semantically matches fresh cards to existing ones (by name and description), and determines what to insert (new patterns), update (existing patterns that were re-extracted), or delete (stale patterns that no longer emerge from extraction). This keeps the catalog in sync with the codebase across repeated runs.

In interactive mode, the pipeline pauses after each stage for user approval. In CI mode (`PATTERN_IQ_CI=true`), all approval gates are skipped.

### Discovery

The `pattern-search` skill queries the Cortex Search service against the `SEARCH_CONTENT` column. Engineers describe their problem in natural language, and the service matches against the synthetic queries to surface relevant patterns. Results include the pattern card with a "Why this matched" explanation.

```
cortex> $pattern-search
> "How do I set up OAuth with a Streamlit app?"
```

Supports filters by category, language, framework, repo, and complexity.

## Project Structure

```
pattern-iq/
├── pyproject.toml                          # Root project config
├── PLAN.md                                 # Architecture & roadmap
├── .cortex/
│   └── skills/
│       ├── pattern-extract/                # Extraction orchestrator
│       │   ├── SKILL.md                    # Pipeline instructions
│       │   └── stages/
│       │       ├── architect/              # Stage 1: file scanning + domain grouping
│       │       │   ├── references/domains.md
│       │       │   └── scripts/tree_scanner.py
│       │       ├── distiller/              # Stage 2: recipe extraction
│       │       │   ├── references/{categories,frameworks,schema,prompt-guide}.md
│       │       │   └── scripts/file_reader.py
│       │       └── librarian/              # Stage 3: synthetic queries + reconciliation + sync
│       │           ├── references/synthetic-queries-guide.md
│       │           └── scripts/
│       │               ├── insert_patterns.py
│       │               └── reconcile_patterns.py
│       └── pattern-search/                 # Discovery skill
│           ├── SKILL.md
│           └── scripts/search.py
├── workflows/
│   └── pattern-iq.yml                      # Template workflow for target repos
├── scripts/
│   └── upload_skills.sh                    # Package + upload skills to Snowflake stage
├── sql/
│   ├── service_account.sql                 # Team CI service account (run once)
│   ├── setup.sql                           # Pattern-IQ database, table, search service, grants
│   └── teardown.sql                        # Drop everything
└── tests/
    ├── test_tree_scanner.py
    ├── test_file_reader.py
    ├── test_insert_patterns.py
    └── test_reconcile_patterns.py
```

## Setup

### Prerequisites

- [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code)
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Snowflake connection configured in `~/.snowflake/connections.toml`

### Snowflake Objects

Run each statement from `sql/setup.sql` against your Snowflake account. This creates:

| Object | Purpose |
|--------|---------|
| `PATTERN_IQ` database | Houses all pattern catalog objects |
| `PATTERN_IQ` role | Scoped access for the CI service account |
| `REUSABLE_PATTERNS` table | Stores extracted pattern cards (19 columns) |
| `SKILLS_STAGE` stage | Stores the skills tarball for CI distribution |
| `PATTERN_SEARCH_SVC` | Cortex Search service indexing `SEARCH_CONTENT` |

The statements are idempotent (`IF NOT EXISTS` / `OR REPLACE`).

### Upload Skills to Stage

After setup, upload the skills so CI workflows can download them:

```bash
./scripts/upload_skills.sh --connection <your_connection>
```

Re-run this whenever you modify anything under `.cortex/skills/`. A GitHub Actions workflow (`pattern-iq-upload-skills.yml` at the aura repo root) automates this on pushes to main that change the skills directory.

## Running Pattern Extraction

### Interactive (local)

Open Cortex Code in a terminal and invoke the skill:

```
cortex> $pattern-extract
```

The skill will ask for a repo path, then run through all three stages with approval gates between each.

To scan a specific subdirectory in a mono-repo:

```
cortex> Run $pattern-extract on the repo at /path/to/monorepo/my-project
```

### CI (GitHub Actions)

The `pattern-iq.yml` workflow template runs the full pipeline headlessly, including reconciliation (insert/update/delete). Copy it from `workflows/pattern-iq.yml` in the pattern-iq project into any target repo's `.github/workflows/` directory.

**Workflow inputs** (all optional):

| Input | Default | Description |
|-------|---------|-------------|
| `target_path` | Root | Subdirectory to scan (for mono-repos) |
| `connection` | `default` | Snowflake connection name |

**Required repo secrets:**

| Secret | Value |
|--------|-------|
| `AIFDE_CI_SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `AIFDE_CI_SNOWFLAKE_USER` | `AIFDE_CI_SVC` |
| `AIFDE_CI_SNOWFLAKE_PRIVATE_KEY` | Private key contents (see [CI Service Account](#ci-service-account)) |

**Trigger:** Go to the repo's Actions tab, select "Pattern IQ", click "Run workflow".

On repeated runs against the same repo, the Librarian's reconciliation step ensures existing patterns are updated and stale patterns are removed — no manual cleanup needed.

### Querying Extracted Patterns

After extraction, verify patterns were inserted:

```sql
SELECT PATTERN_ID, PATTERN_NAME, CATEGORY, COMPLEXITY_SCORE, SOURCE_REPO_LINK
FROM PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS
WHERE REPO_NAME = '<repo_name>'
ORDER BY CREATED_AT DESC;
```

To search patterns interactively:

```
cortex> $pattern-search
```

## CI Service Account

Pattern-IQ uses a shared team service account (`AIFDE_CI_SVC`) for all GitHub Actions workflows that connect to Snowflake. This account uses key-pair authentication — no password.

### Account Details

| Field | Value |
|-------|-------|
| User | `AIFDE_CI_SVC` |
| Type | `SERVICE` (non-interactive, no web UI login) |
| Auth | RSA key-pair |
| Default warehouse | `COMPUTE_WH` |
| Private key location | 1Password vault **"ENG - FDE Dev"** |

The service account is defined in `sql/service_account.sql`. Project-specific roles are granted to it in each project's setup script. For Pattern-IQ, `sql/setup.sql` grants the `PATTERN_IQ` role which provides:

- `USAGE` on `COMPUTE_WH`, `PATTERN_IQ` database, and `PUBLIC` schema
- `READ`/`WRITE` on `SKILLS_STAGE`
- `SELECT`/`INSERT`/`UPDATE`/`DELETE` on `REUSABLE_PATTERNS`
- `USAGE` on `PATTERN_SEARCH_SVC`

### Setting Up a New Repo

To enable the Pattern Extract workflow in a new repo:

1. Retrieve the private key from the **"ENG - FDE Dev"** vault in 1Password
2. Add these secrets in the repo's Settings > Secrets and variables > Actions:
   - `AIFDE_CI_SNOWFLAKE_ACCOUNT` — your Snowflake account identifier
   - `AIFDE_CI_SNOWFLAKE_USER` — `AIFDE_CI_SVC`
   - `AIFDE_CI_SNOWFLAKE_PRIVATE_KEY` — paste the private key contents (including `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` lines)
3. Copy `workflows/pattern-iq.yml` from the pattern-iq project into the repo's `.github/workflows/`
4. Trigger the workflow from the Actions tab

### Key Rotation

To rotate the service account's key pair:

1. Generate a new key pair:
   ```bash
   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out aifde_ci.p8 -nocrypt
   openssl rsa -in aifde_ci.p8 -pubout -out aifde_ci.pub
   ```
2. Update the Snowflake user (as ACCOUNTADMIN):
   ```sql
   ALTER USER AIFDE_CI_SVC SET RSA_PUBLIC_KEY = '<new_public_key>';
   ```
3. Update the private key in the **"ENG - FDE Dev"** 1Password vault
4. Notify repo owners to update their `AIFDE_CI_SNOWFLAKE_PRIVATE_KEY` secret
5. Delete key files from your local machine

## Tests

```bash
uv run pytest tests/ -v
```

Tests cover the pure-Python logic of all three stage scripts (tree scanner, file reader, pattern inserter) and the reconciliation script. No Snowflake connection required — the connector is mocked in tests.
