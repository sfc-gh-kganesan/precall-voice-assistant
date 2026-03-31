# P67 FTUX Improvements Proposal

Improvements to the first-time user experience for internal workflow developers during the dogfooding phase.

## Current Onboarding Flow

1. Download user bundle tarball from GH release
2. Extract tarball
3. Run `./setup.sh` (creates Snowhouse connection, installs CoCo profile)
4. Download `p67` binary from GH release
5. `xattr -cr ./p67 && chmod +x ./p67 && sudo mv ./p67 /usr/local/bin/`
6. Get controld endpoint URL (from Snowsight app or admin)
7. `p67 connection add prod --endpoint <url> --set-default`
8. Generate a PAT (manual Snowsight step)
9. Start building workflows

That's 9 steps with manual URL/PAT copying. Several of these can be automated or eliminated.

---

## A. One-Command Setup

**Problem:** Users must download a tarball, extract it, run a shell script, then separately download and install the CLI binary. Too many manual steps before they can do anything.

**Proposal (Phase 1 — GH):** Create a single curl-installable script (hosted on the GH release) that does everything:

```bash
curl -fsSL https://.../install-p67.sh | bash
```

The script would:
1. Detect platform (darwin-arm64, darwin-x64, linux-x64, etc.)
2. Download the correct `p67` binary from the GH release
3. Install it to `/usr/local/bin/` (or `~/.local/bin/`)
4. Run `cortex profile add p67 -c <connection>` if cortex is installed
5. Print next steps

**Proposal (Phase 2 — Snowflake Stage):** Not all users have access to GH Enterprise. In Phase 2, the GH Actions release workflow uploads the binaries and install script to a Snowflake stage (e.g. `@P67.DIST.RELEASES/`). Users with only Snowflake access can install via:

```bash
snow stage copy @P67.DIST.RELEASES/install.sh ./install.sh && bash ./install.sh
# Or a snow-native approach:
snow stage copy @P67.DIST.RELEASES/p67-darwin-arm64 ./p67 && chmod +x ./p67
```

This requires adding a `snow stage copy` step to the GH release workflow after building binaries. The stage is readable by anyone with `P67_USER_RL`.

**What changes:**
- Phase 1: New `ops/install.sh` script, GH release workflow uploads it
- Phase 2: GH release workflow adds `snow stage copy` step to upload binaries + install script to `@P67.DIST.RELEASES/`
- User bundle README updated to reference both install paths

**Dependencies:** Phase 1 needs GH Enterprise access. Phase 2 needs a Snowflake stage + the release workflow to have a Snowflake connection for upload.

**Complexity:** Low (Phase 1), Medium (Phase 2 — CI/CD pipeline change)

---

## B. Auto-Discover Endpoint

**Problem:** Users need to find the controld endpoint URL manually — either by asking an admin, looking in Snowsight, or running `CALL P67.V1.APP_URL()`. This is friction and a common support question.

**Proposal:** Add a `--discover` flag to `p67 connection add` that auto-discovers the endpoint:

```bash
p67 connection add prod --discover --set-default
```

Under the hood:
1. Use the user's Snowflake connection (from `~/.snowflake/connections.toml` or `config.toml`)
2. Run `snow sql -q "CALL P67.V1.APP_URL()"` to get the endpoint
3. Prompt for PAT (or offer to generate one via `snow sql`)
4. Save the connection

Could also integrate with `snow` CLI's connection selection if multiple connections exist.

**What changes:**
- `tools/p67-cli/src/commands/connection/add.ts` — add `--discover` flag
- New utility to shell out to `snow sql` and parse the result
- Needs the user's Snowflake connection name as input (could default to whatever `snow` defaults to)

**Dependencies:** `snow` CLI must be installed. Most Snowflake developers already have it.

**Complexity:** Medium — needs to handle snow CLI not installed, connection selection, and PAT prompt flow

---

## C. SessionStart Health Check Hook

**Problem:** Users open CoCo and try to build/deploy a workflow, only to discover 5 minutes later that their p67 CLI isn't installed, their connection is stale, or controld is unreachable. No feedback until something fails.

**Proposal:** Add a `SessionStart` hook to the CoCo profile that runs a lightweight health check when CoCo starts:

```json
{
    "hooks": [
        {
            "type": "command",
            "event": "SessionStart",
            "command": "p67-health-check.sh",
            "timeout": 10,
            "source": {
                "snowflake_stage": "@P67.COCO_SKILLS.P67_CLI/scripts/"
            }
        }
    ]
}
```

The script checks:
- Is `p67` in PATH? → "Install p67: ..."
- Does `p67 connection list` show a connection? → "Run: p67 connection add ..."
- Is the default connection's endpoint reachable? → "Controld is down" or nothing (success is silent)

Output is injected into the CoCo session as context, so the agent knows the state and can help fix issues.

**What changes:**
- New `ops/coco-profile/scripts/p67-health-check.sh`
- `ops/coco-profile/profile.json` — add hooks entry
- Profile republish

**Dependencies:** CoCo hooks with `SessionStart` event must be supported (documented in profile schema, but unclear if the `source` field works for hooks yet)

**Complexity:** Low — small shell script + profile.json update. Main risk is whether the hook execution works reliably.

---

## D. Global Workflow Commands via Profile

**Problem:** The CoCo workflow authoring commands (define-workflow, generate-workflow, generate-workflow-code) are installed per-project by `p67 init` into `.claude/commands/`. This means:
- Users can't ask CoCo to create a workflow until after they've scaffolded a project
- Python projects don't get the commands (only TypeScript does — see `init.ts` line 108)
- If the commands are updated, existing projects have stale copies

**Proposal:** Ship these commands through the profile's `commandRepos` field instead:

```json
{
    "commandRepos": [
        {
            "snowflake_stage": "@P67.COCO_SKILLS.P67_CLI/commands/"
        }
    ]
}
```

This makes the commands available in every CoCo session with the p67 profile, regardless of whether the user has run `p67 init` or what language they chose. Updates propagate automatically on `cortex profile sync`.

`p67 init` would stop installing local copies (or keep them as overrides for customization).

**What changes:**
- Upload the three command `.md` files to the Snowflake stage alongside skills
- `ops/coco-profile/profile.json` — add `commandRepos` entry
- `ops/coco-profile/publish.sh` — include commands in stage upload
- Optionally remove command installation from `p67 init` (or keep as fallback)

**Dependencies:** `commandRepos` with Snowflake stage source must be supported by CoCo profiles

**Complexity:** Low — the commands already exist, just need to be distributed via a different channel

---

## E. Workflow Templates via Profile + CLI

**Problem:** `p67 init` creates a blank scaffold with a minimal example (3-node hello-world). The user bundle includes richer examples (hello-world, human-in-the-loop, workflow-editor-template) but they're just docs to read — users have to manually copy code from them.

**Proposal:** This is two things working together:

**E1. Ship templates with the CoCo profile** so CoCo can reference them when helping users scaffold workflows. Templates live on the Snowflake stage alongside skills and commands:

```
@P67.COCO_SKILLS.P67_CLI/
├── skills/
│   ├── p67-cli/
│   └── trigger-workflow/
├── commands/
│   ├── define-workflow.md
│   ├── generate-workflow.md
│   └── generate-workflow-code.md
└── templates/
    ├── hello-world/
    │   ├── src/index.ts
    │   ├── manifest.yaml
    │   └── package.json
    ├── hitl/
    │   └── ...
    └── python-hello/
        └── ...
```

The p67-cli skill's SKILL.md would reference these templates so CoCo knows they exist and can use them when a user says "create a workflow like the hello-world example." CoCo would scaffold the project using the template files as a starting point rather than generating from scratch.

**E2. `p67 init --template` flag** for users who prefer the CLI directly:

```bash
p67 init myworkflow --template hello-world
p67 init myworkflow --template hitl
p67 init myworkflow --template python-hello
```

Templates are embedded in the binary using the same `with { type: 'file' }` pattern we used for the Python SDK. Running `p67 init --template` with no argument lists available templates interactively.

**Key distinction from read-only examples:** A template is a complete, runnable project scaffold — it includes `manifest.yaml`, source files, `package.json`/`requirements.txt`, and `tsconfig.json`. The user gets something they can immediately `p67 build && p67 workflow deploy && p67 workflow run`. Read-only examples are just source code snippets for reference. Templates replace the blank scaffold entirely; examples are supplementary reading.

To make an existing example into a template:
- Ensure it has all required files (manifest.yaml, package.json, etc.)
- Remove any hardcoded account/connection values from manifest.yaml (use placeholders or `p67 manifest from-connection` after scaffolding)
- Verify it builds and runs cleanly from a fresh `p67 init`
- Embed the files in the CLI binary via `with { type: 'file' }` imports

**What changes:**
- New `tools/p67-cli/src/workspace/templates/` directory with template files
- Embed templates in binary via `with { type: 'file' }` imports
- `tools/p67-cli/src/commands/init.ts` — add `--template` flag and selection logic
- `tools/p67-cli/src/workspace/Workspace.ts` — template-aware bootstrap
- Upload templates to Snowflake stage for CoCo profile access
- Update p67-cli skill SKILL.md to reference available templates

**Dependencies:** E2 (CLI flag) has no dependencies. E1 (profile templates) depends on D (commandRepos working with stages).

**Complexity:** Medium — need to embed multiple template sets, handle template selection, ensure each template is self-contained and runnable, and keep templates in sync between the binary and the stage

---

## F. Fix Deploy Cycle (Image Tagging)

**Problem:** We use `:latest` tags for SPCS images. SPCS caches image layers aggressively — pushing a new image with the same `:latest` tag doesn't guarantee SPCS pulls it. We spent significant debugging time on this during the Python SDK fix. `ALTER SERVICE FROM specification_file` only restarts the container if the spec digest changes, and since the tag is the same, the digest doesn't change.

**Proposal:** Change the Makefile to generate a unique tag per build, stash it to a file, and use it across separate `make` invocations:

```makefile
# Tag is generated at build time and written to .build-tag
# so push-controld can read it even if run separately.
TAG_FILE := .build-tag

build-controld:
    $(eval TAG := $(shell git rev-parse --short HEAD)-$(shell date +%s))
    @echo "$(TAG)" > $(TAG_FILE)
    docker build ... -t controld:$(TAG)
    @echo "Built controld:$(TAG)"

push-controld:
    $(eval TAG := $(shell cat $(TAG_FILE) 2>/dev/null || echo "latest"))
    docker tag controld:$(TAG) $(REGISTRY)/controld:$(TAG)
    docker push $(REGISTRY)/controld:$(TAG)
    # Also push as :latest for reference
    docker tag controld:$(TAG) $(REGISTRY)/controld:latest
    docker push $(REGISTRY)/controld:latest
    # Update spec file with the new tag so snow app run picks it up
    sed -i '' 's|image: .*/controld:.*|image: /p67_src/core/img_repo/controld:$(TAG)|' \
        native-app/controld_service_spec.yml
    @echo "Pushed and updated spec to controld:$(TAG)"
```

The tag is stashed in `.build-tag` so that `make build-controld` and `make push-controld` can be run separately (common when debugging build issues or when login expires between build and push). If `.build-tag` doesn't exist (e.g. someone runs `make push-controld` without building first), it falls back to `:latest`.

Then `snow app run` always deploys the new image because the spec file changed (new tag = new digest).

**What changes:**
- `Makefile` — tag generation, `.build-tag` file, auto-update spec on push
- `.gitignore` — add `.build-tag`
- `native-app/controld_service_spec.yml` — updated automatically per push (the committed version can stay as `:latest` and gets overwritten locally)
- Same approach for the runner image

**Dependencies:** None

**Complexity:** Low — Makefile changes only. The pattern is well-established in container deployment workflows.

---

## G. `p67 doctor` Command

**Problem:** When something goes wrong, users don't know where to start debugging. Is the CLI outdated? Is the connection wrong? Is controld down? Is the compute pool suspended? Currently requires checking each thing manually.

**Proposal:** Add `p67 doctor` that runs a comprehensive diagnostic:

```bash
$ p67 doctor
P67 Doctor
  CLI version:     0.1.0 ✓
  Connection:      prod (default) ✓
  Endpoint:        https://xxx.snowflakecomputing.app ✓
  Controld:        healthy (v0.1.0) ✓
  PAT:             valid, expires 2027-01-15 ✓
  Snowflake:       connected as VB ✓
  Compute pool:    IDLE (1 node) ✓
  
All checks passed.
```

When something fails:
```bash
$ p67 doctor
P67 Doctor
  CLI version:     0.1.0 ✓
  Connection:      prod (default) ✓
  Endpoint:        https://xxx.snowflakecomputing.app ✓
  Controld:        unreachable ✗
    → The controld service may be down. Check Snowsight or run:
      CALL P67.V1.APP_URL()
```

Checks in order:
1. CLI version (and whether an update is available)
2. Connection configured (`p67 connection list`)
3. Endpoint URL reachable (HTTP GET /api/health)
4. PAT validity (from health response auth)
5. Snowflake connectivity (if snow CLI available)
6. Compute pool status (from controld health or SHOW COMPUTE POOLS)

**What changes:**
- New `tools/p67-cli/src/commands/doctor.ts`
- Register in CLI command tree
- HTTP health check against controld
- Optional: check for CLI updates against GH releases API

**Dependencies:** None for basic checks. Snowflake connectivity check needs `snow` CLI.

**Complexity:** Medium — straightforward HTTP calls and checks, but needs good error messages for each failure mode

---

## Priority Recommendation

| ID | Proposal | Impact | Effort | Suggested Order |
|----|----------|--------|--------|-----------------|
| B | Auto-discover endpoint | High | Medium | 1st — biggest friction point |
| G | `p67 doctor` | High | Medium | 2nd — reduces support burden |
| C | SessionStart health check | Medium | Low | 3rd — quick win with profile |
| D | Global workflow commands | Medium | Low | 4th — quick win with profile |
| F | Fix deploy cycle | Medium | Low | 5th — developer productivity |
| E | `p67 init --template` | Medium | Medium | 6th — nicer but not blocking |
| A | One-command setup | High | Medium | 7th — needs GH release infra |
