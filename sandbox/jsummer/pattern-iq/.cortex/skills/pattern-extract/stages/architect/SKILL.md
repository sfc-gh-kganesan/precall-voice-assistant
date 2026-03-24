# Phase 1: Architect (Contextual Scoping)

Scans the repo structure and groups files into logical domains with utility scores.

Load `<SKILL_DIRECTORY>/references/domains.md` for the domain taxonomy.

## Step 1.1: Identify Target Repository

**Ask** the user for the repo path. Default to the current working directory.

**Auto-detect metadata:**

1. Find the git root:
```bash
git -C <repo_path> rev-parse --show-toplevel 2>/dev/null
```

2. Get the remote URL:
```bash
git -C <repo_path> remote get-url origin 2>/dev/null
```

3. Derive fields:
   - `repo_name`: basename of the target scan directory (NOT the git root). In a monorepo where the scan target is a subdirectory (e.g., `/repo/my-project`), use `my-project`, not the monorepo root name.
   - `repo_url`: convert SSH to HTTPS if needed (e.g., `git@github.com:org/repo.git` → `https://github.com/org/repo`)
   - `source_repo_link`: `repo_url` value — this will be written to `SOURCE_REPO_LINK` in the database. Carry this value through to Phase 2 pattern cards.
   - `project_root`: the git root path
   - If no git remote, use directory name as `repo_name`, leave `repo_url` and `source_repo_link` empty

## Step 1.2: Run Tree Scanner

```bash
uv run --project <SKILL_DIRECTORY> python <SKILL_DIRECTORY>/scripts/tree_scanner.py <repo_path> --project-root <git_root> --output /tmp/tree-scan.json --summary
```

Parse summary. Present: "Scanned N files across M extensions"

## Step 1.3: Domain Grouping + Utility Scoring

Using the domain taxonomy from `<SKILL_DIRECTORY>/references/domains.md`, group each file into a logical domain using file paths, extensions, dependencies, and head content. Assign utility scores:
- **high**: Custom business logic, unique algorithms, non-trivial orchestration
- **medium**: Standard integration code, config with customization
- **low**: Boilerplate, trivial helpers, empty/auto-generated files

## Step 1.4: Output Manifest

Save to `/tmp/architect-manifest.json`. The manifest **must** use the following schema (field names must match exactly for `file_reader.py` compatibility):

```json
{
  "repo_name": "my-project",
  "repo_url": "https://github.com/org/repo",
  "project_root": "/path/to/git/root",
  "domains": [
    {
      "name": "domain-name",
      "description": "What this domain covers.",
      "files": [
        {"path": "relative/to/git-root/file.py", "utility_score": "high", "line_count": 150},
        {"path": "relative/to/git-root/other.py", "utility_score": "medium", "line_count": 45}
      ]
    }
  ]
}
```

**Critical field names**: Each domain must use `"name"` (not `"domain"`). Each file must use `"utility_score"` (not `"utility"`). These are required by `file_reader.py`.

Present summary by domain.

**MANDATORY STOPPING POINT**: First, check if the environment variable `PATTERN_IQ_CI` is set to `true`. If it is, skip this approval and proceed directly to Phase 2. Otherwise, use the `AskUserQuestion` tool to get explicit approval:
- Question: "Do you approve these domain groupings and utility scores?"
- Options: "Approved" (proceed to Phase 2), "Needs changes" (user specifies what to adjust)
Do NOT proceed to Phase 2 until the user selects "Approved".
