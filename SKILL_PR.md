# PR Skill

Generic workflow for creating and managing pull requests using the `gh` CLI.

## Pre-PR Checklist

Before creating a PR, always run CI checks locally:

```bash
pnpm run ci                         # Run all CI checks
pnpm run check                      # Linting only
pnpm run type:check                 # TypeScript only
pnpm run build                      # Build only
```

## Creating a PR

### 1. Check current state

```bash
git status                          # Uncommitted changes
git log --oneline -5                # Recent commits
git diff main...HEAD --stat         # Changes vs main
```

### 2. Write a good PR description

A good PR description should include:

**Title**: Use conventional commits format: `feat|fix|refactor|docs|style|test(scope): description`

**Body structure**:
- **Summary**: 1-2 sentences explaining WHY (the problem/motivation), not just WHAT
- **Changes**: Bullet points of what was added/modified, organized by area (API, CLI, etc.)
- **Usage**: Show how to use the new feature with concrete examples (curl, CLI commands)
- **Schema/Config**: If adding new config options, show the format
- **Test plan**: Checklist of manual verification steps

### 3. Create the PR

```bash
gh pr create --title "feat(scope): description" --body "$(cat <<'EOF'
## Summary
Brief explanation of WHY this change exists (the problem it solves).

## Changes

### API
- New endpoint `POST /thing` that does X
- Updated `GET /other` to support Y parameter

### CLI  
- Added `--flag` option to `command`
- Interactive mode now prompts for X

## Usage

### API
```bash
curl -X POST http://localhost:3000/thing \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

### CLI
```bash
my-cli command --flag value
```

## Configuration

New config options in `config.yaml`:
```yaml
newField:
  option: "value"        # Description
  required: true         # Whether required
```

## Test plan
- [ ] Test scenario 1
- [ ] Test scenario 2

.... Generated with [Cortex Code](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents)
EOF
)"
```

## Viewing PR Information

```bash
gh pr view <PR_NUMBER>
gh pr view <PR_NUMBER> --json title,body,state,reviews,comments
gh pr view <PR_NUMBER> --web        # Open in browser
```

## Listing PRs

```bash
gh pr list                          # Open PRs
gh pr list --state all              # All PRs
gh pr list --author @me             # Your PRs
gh pr list --search "keyword"       # Search PRs
```

## PR Status and Checks

```bash
gh pr status                        # Status of relevant PRs
gh pr checks <PR_NUMBER>            # CI check status
```

## Comments and Reviews

```bash
gh api repos/{owner}/{repo}/pulls/<PR_NUMBER>/comments
gh api repos/{owner}/{repo}/pulls/<PR_NUMBER>/reviews
gh pr review <PR_NUMBER> --approve
gh pr review <PR_NUMBER> --request-changes --body "feedback"
```

## Merging

```bash
gh pr merge <PR_NUMBER> --squash    # Squash and merge
gh pr merge <PR_NUMBER> --merge     # Merge commit
gh pr merge <PR_NUMBER> --rebase    # Rebase and merge
```

## Other Commands

```bash
gh pr diff <PR_NUMBER>              # View diff
gh pr checkout <PR_NUMBER>          # Checkout locally
gh pr close <PR_NUMBER>             # Close without merging
gh pr reopen <PR_NUMBER>            # Reopen closed PR
gh pr edit <PR_NUMBER> --title "x"  # Edit PR metadata
```
