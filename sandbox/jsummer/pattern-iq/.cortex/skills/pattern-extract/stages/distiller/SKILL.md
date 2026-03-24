# Phase 2: Distiller (Pattern Extraction)

Extracts interaction patterns ("Recipes") from high-utility code.

Load these reference files:
- `<SKILL_DIRECTORY>/references/prompt-guide.md` — extraction quality standards
- `<SKILL_DIRECTORY>/references/categories.md` — pattern category taxonomy
- `<SKILL_DIRECTORY>/references/frameworks.md` — framework taxonomy
- `<SKILL_DIRECTORY>/references/schema.md` — full Snowflake column schema for Pattern Cards

## Step 2.1: Read High-Utility Files

```bash
uv run --project <SKILL_DIRECTORY> python <SKILL_DIRECTORY>/scripts/file_reader.py --manifest /tmp/architect-manifest.json --threshold high --repo-root <project_root> --output /tmp/distiller-input.json
```

**Validation**: After running, verify the output has non-empty domains. If `"domains": []`, the manifest field names are likely wrong — check that domains use `"name"` and files use `"utility_score"` (see architect manifest schema).

If any domain groups hit the 60K character context budget (check `truncated_count > 0`), read the truncated files directly before extraction to ensure complete coverage.

## Step 2.2: Extract Recipes

For each domain group, analyze code holistically. DO NOT extract individual functions. Instead, identify the core **Recipe** — the interaction pattern.

Apply:
> "Analyze these files as a group. Identify the core 'Recipe' — the interaction pattern showing how these components work together to solve a specific problem. Strip away customer-specific names. Output a generic, reusable template."

For each identified Recipe, generate a **Pattern Card** with these fields:

| Field | Description |
|---|---|
| `pattern_name` | Short descriptive name |
| `category` | From categories.md taxonomy |
| `description` | 2-3 sentences explaining the interaction pattern |
| `abstracted_code` | Generic template with `<PLACEHOLDER>` tokens |
| `dependency_graph` | List of package dependencies |
| `complexity_score` | 1-5 with justification |
| `usage_notes` | When and how to use this pattern |
| `tags` | Domain-specific search terms |
| `language` | Programming language (e.g., `python`) |
| `framework` | From frameworks.md taxonomy |
| `repo_name` | From manifest `repo_name` field |
| `repo_url` | From manifest `repo_url` field |
| `source_repo_link` | Same as `repo_url` — maps to `SOURCE_REPO_LINK` column in Snowflake |

See `<SKILL_DIRECTORY>/references/schema.md` for the full column definitions in the target table.

## Step 2.3: Quality Gates

Every card must pass:
- Description is 2-3 sentences
- Abstracted code has at least one `<PLACEHOLDER>`
- Complexity score 1-5 with justification
- Tags include domain-specific terms
- `source_repo_link` is populated (from manifest `repo_url`)

## Step 2.4: Approve Pattern Cards

**MANDATORY STOPPING POINT**: First, check if the environment variable `PATTERN_IQ_CI` is set to `true`. If it is, skip this approval and proceed directly to Phase 3. Otherwise, use the `AskUserQuestion` tool to get explicit approval:
- Question: "Do you approve these Pattern Cards?"
- Options: "Approved" (proceed to Phase 3), "Needs changes" (user specifies what to adjust)
Do NOT proceed to Phase 3 until the user selects "Approved".

Save to `/tmp/pattern-cards.json`.
