---
name: pattern-search
description: >
  Search the pattern catalog for reusable interaction patterns and recipes.
  Use when: looking for patterns, "find pattern", "how do we do X",
  "any examples of", "search patterns", "pattern for", "show me code for",
  "what patterns exist for", discovering reusable code.
---

# Pattern Search

## Prerequisites

- `uv` installed (`uv --version`)
- Snowflake connection with access to `PATTERN_IQ` database
- Cortex Search service `PATTERN_SEARCH_SVC` must be active

## Workflow

### Step 1: Get Search Query

Take the user's natural language query. If the user also specifies filters (language, category, framework, repo, complexity), note them.

### Step 2: Execute Search

```bash
SNOWFLAKE_CONNECTION_NAME=<connection> uv run --project <SKILL_DIRECTORY> python <SKILL_DIRECTORY>/scripts/search.py \
  --query "<user_query>" \
  [--category <category>] \
  [--language <language>] \
  [--framework <framework>] \
  [--repo-name <repo>] \
  [--max-complexity <n>] \
  [--limit 5]
```

Parse the JSON output.

### Step 3: Present Results

Display top results as Pattern Cards:

```
| # | Pattern Name | Category | Complexity | Language | Repo |
|---|-------------|----------|------------|----------|------|
| 1 | ... | ... | .../5 | ... | ... |
```

For each result, show:
- **Description** (2-3 sentences)
- **Why this matched**: Relevant synthetic queries from the pattern

### Step 4: User Actions

Offer these actions:
1. **View abstracted code** — display the clean-room template for a selected pattern
2. **View dependencies** — show the dependency graph and complexity details
3. **Refine search** — run a new query with adjusted terms or filters
4. **Copy snippet** — offer to insert the abstracted code into the user's current project

## Stopping Points

- After Step 3: wait for user to select an action

## Output

Search results from the Pattern-IQ catalog displayed to the user.
