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

After presenting results, offer these actions:

1. **View abstracted code** — Display the clean-room template code for a selected pattern. Explain that this is a generalized, reusable version of the pattern with placeholders (e.g., database names, table names, config values) that the engineer can customize for their specific use case. Walk through the key placeholders and explain what each one controls. If the code was not included in the initial response, run a follow-up query: `--query "Show me the abstracted code for the <pattern_name> pattern"`.

2. **View source repo** — Display the source repository link for a selected pattern so the engineer can study the original, full implementation. If the link was not in the initial response, run a follow-up query: `--query "What is the source repo link for the <pattern_name> pattern?"`.

3. **View dependencies** — Show the dependency graph and complexity details for a selected pattern. Run a follow-up query if needed: `--query "Show me the dependencies for the <pattern_name> pattern"`.

4. **Ask follow-up** — The engineer can ask a follow-up question to narrow results, compare patterns, get more detail, or explore related patterns. Run the script again with the new query and optionally the same `--context`.

5. **Copy snippet** — Offer to insert the abstracted code into the engineer's current project, adapting the placeholders to the project's actual values where possible.

## Stopping Points

- After Step 3: wait for the user to select an action
- After any Step 4 action: wait for the user to select another action or end

## Output

Pattern discovery results from the Pattern Marketplace Agent displayed to the user, with source repo links and abstracted code readily accessible.
