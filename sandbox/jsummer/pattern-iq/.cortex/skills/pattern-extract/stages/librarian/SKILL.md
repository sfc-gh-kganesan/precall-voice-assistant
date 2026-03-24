# Phase 3: Librarian (Semantic Indexing)

Generates synthetic queries, reconciles fresh patterns against existing ones in Snowflake, and syncs the catalog (insert new, update existing, delete stale).

Load `<SKILL_DIRECTORY>/references/synthetic-queries-guide.md` for query generation guidance and quality standards.

## Step 3.1: Generate Synthetic Queries

For each pattern in `/tmp/pattern-cards.json`, generate 5-10 synthetic queries — questions an engineer would ask when they have the problem this pattern solves. Must be problem-first, specific, and natural. Follow the rules and examples in the synthetic queries guide.

## Step 3.2: Build Search Content

```
search_content = pattern_name + " " + description + " " + usage_notes + " " + " ".join(synthetic_queries)
```

## Step 3.3: Approve Queries

**MANDATORY STOPPING POINT**: First, check if the environment variable `PATTERN_IQ_CI` is set to `true`. If it is, skip this approval and proceed directly to Step 3.4. Otherwise, use the `AskUserQuestion` tool to get explicit approval:
- Question: "Do you approve these synthetic queries?"
- Options: "Approved" (proceed to insert into Snowflake), "Needs changes" (user specifies what to adjust)
Do NOT proceed to Step 3.4 until the user selects "Approved".

## Step 3.4: Reconcile with Existing Patterns

Before writing to Snowflake, reconcile the fresh pattern cards against what already exists for this repo.

### 3.4.1: Fetch existing patterns

```bash
uv run --project <SKILL_DIRECTORY> python <SKILL_DIRECTORY>/scripts/reconcile_patterns.py \
  --input /tmp/pattern-cards.json \
  --connection <connection_name> \
  --output /tmp/reconciliation-manifest.json
```

Read `/tmp/reconciliation-manifest.json`. It contains:
- `existing_patterns`: array of `{pattern_id, pattern_name, description}` currently in Snowflake for this repo
- `fresh_cards_count`: how many fresh cards were extracted

### 3.4.2: Match fresh cards to existing patterns

If `existing_patterns` is empty, this is the first run — skip matching. All fresh cards are inserts.

Otherwise, for each fresh pattern card, determine if it corresponds to an existing pattern:
- **Match criteria**: the pattern solves the same problem. Compare by semantic similarity of name and description — NOT exact string equality. Pattern names may drift slightly across extractions (e.g., "OAuth Token Refresh" vs "OAuth Token Refresh with Retry").
- **Matched**: carry forward the existing `pattern_id`, set `"action": "update"` on the card
- **Unmatched fresh card**: assign a new UUID, set `"action": "insert"`
- **Unmatched existing pattern** (no fresh card matched it): add an entry with only `pattern_id`, `pattern_name`, and `"action": "delete"` — this pattern is stale and should be removed

### 3.4.3: Approve reconciliation

Present a reconciliation summary table:

```
| Action | Pattern Name | Existing ID | Notes |
|--------|-------------|-------------|-------|
| update | OAuth Token Refresh with Retry | abc-123 | Matched "OAuth Token Refresh" |
| insert | New Redis Cache Pattern | (new) | No existing match |
| delete | Deprecated Auth Flow | def-456 | No longer extracted |
```

**MANDATORY STOPPING POINT**: Check `PATTERN_IQ_CI`. If `true`, auto-approve. Otherwise, use `AskUserQuestion`:
- Question: "Do you approve this reconciliation plan?"
- Options: "Approved" (proceed to sync), "Needs changes" (user adjusts matches)

## Step 3.5: Sync to Snowflake

Save reconciled patterns to `/tmp/final-patterns.json`. Each entry must have:
- `action`: one of `"insert"`, `"update"`, or `"delete"`
- `pattern_id`: existing ID (for update/delete) or new UUID (for insert)
- All pattern fields: `pattern_name`, `category`, `description`, `abstracted_code`, `source_repo_link`, `repo_name`, `complexity_score`, `dependencies`, `dependency_graph`, `synthetic_queries`, `usage_notes`, `tags`, `language`, `framework` (not required for `delete` entries)

Then run:

```bash
uv run --project <SKILL_DIRECTORY> python <SKILL_DIRECTORY>/scripts/insert_patterns.py --input /tmp/final-patterns.json --connection <connection_name>
```

The script handles all three actions: INSERT new rows, UPDATE existing rows (preserving `PATTERN_ID` and `CREATED_AT`, refreshing `UPDATED_AT`), and DELETE stale rows.

## Step 3.6: Summary

```
Synced patterns for <repo_name>: inserted X, updated Y, deleted Z.
Categories: auth (2), llm-orchestration (1), ...
```
