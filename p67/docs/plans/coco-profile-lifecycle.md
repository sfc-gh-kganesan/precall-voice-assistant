# CoCo Profile Lifecycle — How Profiles Flow Through the System

## 1. Authoring (admin/developer creates the profile + uploads skills)

```
SKILL.md files          Profile Registry            Snowflake Stage
(on stage or bundled)   (Snowflake table)           @DB.SCHEMA.STAGE/skills/
    │                       │                           │
    │                       │                           │
    ▼                       ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  CORTEX_CODE.CONFIG.PROFILE_REGISTRY                            │
│                                                                 │
│  CONFIG_NAME: "my-profile"                                      │
│  SKILL_REPOS: [{"snowflake_stage": "@DB.SCHEMA.STAGE/skills/"}] │
│  SETTINGS_OVERRIDES: {"model": "opus"}                          │
│  ENV_VARS: {"MY_VAR": "value"}                                  │
│  HOOKS: {...}                                                   │
│  ... (metadata, version, active flag)                           │
└─────────────────────────────────────────────────────────────────┘
```

Skills can be provided two ways:
1. **Stage-based** (preferred): Uploaded to a Snowflake stage referenced in `SKILL_REPOS`
2. **Bundled**: Shipped as files inside the workflow zip under `skills/`

## 2. Runtime Flow (P67 workflow in SPCS calls cortexCode with profile)

```
┌─────────────────────────────────────────────────────────────┐
│  sdk.cortexCode({ prompt: '...', profile: 'my-profile' })   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ 1. Create temp SNOWFLAKE_HOME
                       │    (e.g. /tmp/p67-cortex-xxxx/)
                       │
                       │ 2. Write BOTH files to $SNOWFLAKE_HOME/:
                       │    - config.toml      (CoCo LLM auth via cortex -p)
                       │    - connections.toml  (cortex profile add SQL auth)
                       │    Note: connections.toml uses [default] header,
                       │    NOT [connections.default]
                       │
                       │ 3a. PRIMARY: cortex profile add <name> --force -c default
                       │     (uses connections.toml written in step 2)
                       │     -> CoCo writes profile JSON itself
                       │
                       │ 3b. FALLBACK (if 3a fails): direct SQL query
                       │     SELECT from CORTEX_CODE.CONFIG.PROFILE_REGISTRY
                       │     via SDK's Snowflake driver (works with PAT)
                       │     -> write profile JSON manually to:
                       │       $SNOWFLAKE_HOME/cortex/profiles/my-profile.json
                       │
                       │ 4a. PRIMARY: Download skills from stage
                       │     - Query SKILL_REPOS from PROFILE_REGISTRY
                       │     - USE SCHEMA <db.schema> (from stage path)
                       │     - CREATE TEMPORARY FILE FORMAT p67_raw_text
                       │     - LIST @stage/skills/ -> enumerate skill dirs
                       │     - SELECT $1::VARCHAR FROM @stage/skills/<name>/SKILL.md
                       │       (FILE_FORMAT => p67_raw_text)
                       │     -> write to $SNOWFLAKE_HOME/cortex/skills/<name>/SKILL.md
                       │
                       │ 4b. FALLBACK (if stage download fails):
                       │     Copy bundled skills from workflow dir
                       │     /workflow/skills/<name>/ ->
                       │     $SNOWFLAKE_HOME/cortex/skills/<name>/
                       │
                       │ 5. Write skills.json -> $SNOWFLAKE_HOME/cortex/skills.json
                       │
                       │ 6. Invoke: cortex -p "..." --profile my-profile
                       │                           --skills /tmp/.../skills.json
                       │    (SNOWFLAKE_HOME points to temp dir)
                       │
                       ▼
              ┌──────────────────┐
              │  cortex CLI      │
              │  reads profiles/ │ <- finds my-profile.json
              │  reads skills/   │ <- finds my-skill/SKILL.md (local)
              │  runs prompt     │
              └──────────────────┘
                       │
                       │ 7. finally: rm -rf $SNOWFLAKE_HOME
```

## 3. Skill Resolution: Stage Download vs Bundled

### Stage Download (preferred)

The SDK downloads skills from Snowflake stages using its own SQL connection (not
CoCo's internal SQL driver). This works because:

- The SDK writes `connections.toml` with PAT auth to `$SNOWFLAKE_HOME`
- The SDK uses its own Snowflake driver (Node.js `snowflake-sdk` or Python
  `snowflake-connector-python`) which authenticates correctly with PAT
- A `USE SCHEMA` is issued before creating the temp file format to avoid
  "no current schema" errors
- Files are read via `SELECT $1::VARCHAR FROM @stage/file (FILE_FORMAT => name)`

This is preferred because skills are managed centrally on a stage and don't need
to be rebuilt/redeployed with each workflow version.

### Bundled Skills (fallback)

Skills can also be bundled with the workflow zip under `skills/`. This is the
fallback if stage download fails (e.g., stage doesn't exist, permissions issue,
network error). The SDK copies them to `$SNOWFLAKE_HOME/cortex/skills/` before
running CoCo.

| Approach              | Works in SPCS? | Pros                              | Cons                           |
|-----------------------|----------------|-----------------------------------|--------------------------------|
| Stage download (SDK)  | Yes            | Centralized, no rebuild needed    | Needs READ grant on stage      |
| Bundled (local copy)  | Yes            | Self-contained, no grants needed  | Must redeploy to update skills |

### Why the SDK Downloads (not CoCo)

CoCo's internal SQL driver uses a different auth path that doesn't work reliably
with PAT tokens in SPCS. The SDK's own SQL driver works correctly, so the SDK
handles the download and writes the files locally before spawning CoCo.

## 4. What Works in SPCS

| Feature                     | Works? | Notes                                          |
|-----------------------------|--------|-------------------------------------------------|
| Profile fetch from registry | Yes    | Via `cortex profile add` or SDK SQL fallback    |
| --profile flag applied      | Yes    | CoCo reads local JSON                          |
| settingsOverrides           | Yes    | In-memory, no SQL                              |
| envVars                     | Yes    | In-memory, no SQL                              |
| Skills (stage, SDK download)| Yes    | SDK downloads via its own SQL connection        |
| Skills (bundled)            | Yes    | Files on disk, copied before CoCo runs         |
| Skills (CoCo native)        | No     | CoCo SQL driver hangs with PAT auth            |
| System prompt (stage)       | No     | CoCo SQL driver issue (same as above)          |
| MCP servers (stage source)  | No     | CoCo SQL driver issue                          |
| Hooks (inline prompt)       | Yes    | No download needed                             |

## 5. Workflow Author Guide

### Option A: Skills on a Stage (recommended)

Upload skills to a Snowflake stage and reference it in the profile registry:

```sql
-- Upload skill
PUT file:///path/to/secret-code/SKILL.md
    @MY_DB.MY_SCHEMA.MY_STAGE/skills/secret-code/SKILL.md
    AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Update profile to reference the stage
UPDATE CORTEX_CODE.CONFIG.PROFILE_REGISTRY
SET SKILL_REPOS = '[{"snowflake_stage": "@MY_DB.MY_SCHEMA.MY_STAGE/skills/"}]'
WHERE CONFIG_NAME = 'my-profile';
```

Grant READ on the stage to the role used by the workflow runner:

```sql
GRANT READ ON STAGE MY_DB.MY_SCHEMA.MY_STAGE TO ROLE P67_USER_RL;
```

### Option B: Bundled Skills (self-contained)

Place skills in the workflow directory:

```
my-workflow/
├── skills/
│   └── my-skill/
│       └── SKILL.md          <- required; contains skill frontmatter + body
├── src/
│   └── index.ts
└── manifest.yaml
```

`p67 build` includes the `skills/` directory in the workflow zip automatically.

### Limitations

- Skills must be **direct children** of `skills/`. Nested subdirectories
  (e.g., `skills/parent/child/SKILL.md`) are not supported.
- Skills auto-discover from the `description` field in SKILL.md frontmatter.
  The `$skill-name` prefix in prompts is optional.
- Stage skills override bundled skills of the same name when both are present.

## 6. connections.toml Format

CoCo uses `connections.toml` (not `config.toml`) for SQL operations like
`cortex profile add`. The format differs from `config.toml`:

```toml
# connections.toml - uses [default] header
[default]
account = "MY-ACCOUNT"
user = "MY_USER"
authenticator = "PROGRAMMATIC_ACCESS_TOKEN"
token = "<pat>"
warehouse = "MY_WH"
database = "MY_DB"
schema = "PUBLIC"
```

This is different from `config.toml` which uses `[connections.default]`.

## 7. References

- CoCo Profile Deployment Guide: see internal docs for registry DDL
- Registry table: `CORTEX_CODE.CONFIG.PROFILE_REGISTRY`
- Example workflow: `workflows/test/coco-profile/`
- SDK implementation (TS): `services/controld/src/lib/sdk-impl.ts`
- SDK implementation (Python): `packages/workflow-sdk-python/p67_sdk/sdk.py`
- Test workflow (stage only): `qt_stage` — verifies stage download without bundled skills
