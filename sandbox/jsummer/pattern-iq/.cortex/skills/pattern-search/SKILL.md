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
- Cortex Agent `PATTERN_IQ.PUBLIC.PATTERN_MARKETPLACE_AGENT` must exist and be active

## Workflow

### Step 1: Get Search Query

Take the user's natural language query. The agent handles intent routing automatically, so the user does not need to specify filters -- they can describe what they're building in plain English.

If the user provides additional context about their project (e.g., "I'm building a Streamlit RAG app"), capture it separately as context.

### Step 2: Execute Search

```bash
SNOWFLAKE_CONNECTION_NAME=<connection> uv run --project <SKILL_DIRECTORY> python <SKILL_DIRECTORY>/scripts/search.py \
  --query "<user_query>" \
  [--context "<what the user is building>"] \
  [--connection <connection_name>]
```

Parse the JSON output. The response has this structure:
```json
{
  "text": "Agent narrative response with pattern details",
  "citations": [...],
  "request_id": "..."
}
```

### Step 3: Present Results

Display the agent's response to the user. The agent is instructed to return results in a technical, concise format. When presenting results:

1. **Pattern summary table** — If the agent returns multiple patterns, format them as:

```
| # | Pattern Name | Category | Language | Framework | Complexity |
|---|-------------|----------|----------|-----------|------------|
| 1 | ... | ... | ... | ... | .../5 |
```

2. **Source repository links** — For each pattern, prominently display the source repo link as a clickable hyperlink: `[repo_name](source_repo_link)`. Engineers will want to visit these to study the original implementation in context. If the agent response includes repo URLs, extract and surface them. If not, note that the user can ask for source links in a follow-up.

3. **Description** — 2-3 sentence summary per pattern explaining what it does and when to use it.

### Step 4: User Actions

Offer these actions:
1. **View abstracted code** — display the clean-room template for a selected pattern
2. **View dependencies** — show the dependency graph and complexity details
3. **Refine search** — run a new query with adjusted terms or filters
4. **Copy snippet** — offer to insert the abstracted code into the user's current project
5. **Star pattern** — star a selected pattern to show support or indicate it was useful. Execute via SQL: `CALL PATTERN_IQ.PUBLIC.STAR_PATTERN('<PATTERN_ID>')`
6. **Remove pattern** — permanently delete a selected pattern from the catalog. Confirm the pattern name and ID with the user before executing. Execute via SQL: `CALL PATTERN_IQ.PUBLIC.REMOVE_PATTERN('<PATTERN_ID>')`

## Stopping Points

- After Step 3: wait for the user to select an action
- After any Step 4 action: wait for the user to select another action or end

## Output

Pattern discovery results from the Pattern Marketplace Agent displayed to the user, with source repo links and abstracted code readily accessible.
