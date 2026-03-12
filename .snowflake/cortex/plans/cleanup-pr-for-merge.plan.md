# Plan: Clean Up PR for Merge

## Current State
- 4 commits on branch (1 real + 3 test artifacts)
- Stale local tag `p67-cli-v0.1.0-`
- Working tree clean

## Steps

1. **Delete stale local tag** `p67-cli-v0.1.0-` (remote tag was already deleted earlier)
2. **Squash all 4 commits into one** using soft reset to main + re-commit:
   - `git reset --soft main`
   - `git commit -m "ops(p67-cli): create GH workflow for distro"`
3. **Force-push** the cleaned branch to origin
4. **Verify** the branch has exactly 1 clean commit ahead of main

## Result
PR will show a single commit: `ops(p67-cli): create GH workflow for distro`
