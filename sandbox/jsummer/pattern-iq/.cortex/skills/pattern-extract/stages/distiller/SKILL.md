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

This writes:
- `/tmp/distiller-input.json` — a manifest listing each domain and its per-domain file path
- `/tmp/distiller-domain-0.json`, `/tmp/distiller-domain-1.json`, etc. — one file per domain containing the source code content

**Validation**: After running, read `/tmp/distiller-input.json` and verify `domain_count` is > 0. If 0, the manifest field names are likely wrong — check that domains use `"name"` and files use `"utility_score"` (see architect manifest schema).

Then read each per-domain file (`/tmp/distiller-domain-N.json`) individually to get the source code for extraction. Each file is small enough to read without truncation.

Do NOT use the `read` tool to re-read source files from the repository. The per-domain files are your primary and sufficient source — the 60K-per-domain budget provides enough context for pattern extraction. Even if content appears truncated within a domain file, extract patterns from what is available.

## Step 2.2: Extract Recipes

For each domain group, analyze code holistically. DO NOT extract individual functions. Instead, identify the core **Recipe** — the interaction pattern.

Apply:
> "Analyze these files as a group. Identify the core 'Recipe' — the interaction pattern showing how these components work together to solve a specific problem. Strip away customer-specific names. Output a generic, reusable template."

### CI Mode (inline extraction)

When `PATTERN_IQ_CI=true`, extract patterns **directly in the main agent context** — do NOT launch subagents of any type. Due to a known platform limitation, subagents cannot write files in headless mode.

1. Read `/tmp/distiller-input.json` to get the domain manifest (already done in Step 2.1).
2. For each domain, read its per-domain file (`/tmp/distiller-domain-N.json`) and generate one Pattern Card from the code content.
3. Collect all cards into a single JSON array.
4. Write the complete array to `/tmp/pattern-cards.json` using the Write tool.
5. Do NOT re-read source files from the repository with the `read` tool — the per-domain files have all content needed.
6. Skip to Step 2.3 (Quality Gates).

> **Large repo caution**: Inline extraction processes domains sequentially in a single agent context. For repos with more than ~10 high-utility domains, prefer running the extraction locally in interactive mode, which uses parallel background subagents for better performance and accuracy.

### Interactive Mode (parallel subagent extraction)

When `PATTERN_IQ_CI` is NOT set (interactive use) and there are 4 or more domains, use the `Task` tool with the custom `pattern-extractor` subagent to extract patterns in batches:

1. **Balance batches**: sort domains by total content size (largest first), then distribute round-robin across 3-4 batches to balance load evenly. Do not just split sequentially.
2. For each batch, use bash to write the batch data to `/tmp/distiller-batch-N.json`
3. **Launch subagents**: For each batch, launch a `pattern-extractor` subagent (`subagent_type="pattern-extractor"`, `output_var="batch_N_status"`). Try `run_in_background=true` first. If the first call returns an error containing "not enabled", fall back to `run_in_foreground=true` for all remaining batches.
   The prompt must instruct the subagent to:
   - Read `/tmp/distiller-batch-N.json`
   - Extract Pattern Cards for each domain
   - Write the JSON array to `/tmp/distiller-batch-N-result.json` using the Write tool
   - Output a one-line summary as final text: "Wrote N cards to /tmp/distiller-batch-N-result.json"
4. After all subagents complete, verify each `/tmp/distiller-batch-N-result.json` exists and contains a valid JSON array.
5. **Retry**: if any result file is missing or invalid, re-launch that batch once as a foreground subagent (`run_in_foreground=true`).
6. Merge all batches using the merge script:
   ```bash
   uv run --project <SKILL_DIRECTORY> python <SKILL_DIRECTORY>/scripts/merge_batches.py --batch-dir /tmp --output /tmp/pattern-cards.json
   ```

For fewer than 4 domains, process them in a single batch (one subagent) or in the main agent context.

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
