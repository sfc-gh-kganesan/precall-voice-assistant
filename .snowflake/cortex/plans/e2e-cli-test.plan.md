# Plan: E2E CLI Test with Downloaded Binary

## Goal
Verify the downloaded p67 binary works end-to-end for the local development workflow: init → build.

## Steps

1. **`p67 init`** — Scaffold a new project in `/tmp/test-p67` using TypeScript
2. **Inspect** — Verify the scaffolded structure matches expectations (p67.yml, manifest.yaml, src/, package.json)
3. **`p67 build`** — Build the project, verify build output directory is created
4. **`p67 workflow deploy`** — Attempt a deploy to verify the bundle is valid (this will hit the aifde server — we can skip if you want to stay fully local)
5. **Clean up** — Remove temp directory

## Note
Steps 1-3 are fully local. Step 4 requires the `aifde` connection. We can skip deploy if you want to keep it strictly local.
