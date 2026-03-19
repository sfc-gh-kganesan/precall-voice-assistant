# P67 CoCo Skill Distribution

This directory contains scripts for publishing and distributing the P67 CLI skill via the Cortex Code (CoCo) profile system.

## Architecture

```
p67/ops/coco-profile/
├── README.md                        -- This file
├── profile.json                     -- Profile definition (published to registry)
├── publish.sh                       -- Publishes profile + uploads skill to stage
├── check-distribution.sh            -- Shows who has P67_USER_RL + onboarding instructions
├── setup.sh                         -- User onboarding (connection + profile install)
├── Makefile                         -- One-shot publish with version bumping
└── skills/
    └── p67-cli/
        ├── SKILL.md                 -- The skill file (CLI reference for CoCo)
        └── templates/
            └── quickstart.md        -- Quick-reference patterns
```

### Where things live on Snowflake (Snowhouse)

| Object           | Location                               | Purpose                                         |
| ---------------- | -------------------------------------- | ----------------------------------------------- |
| Profile registry | `CORTEX_CODE.CONFIG.PROFILE_REGISTRY`  | Central registry all CoCo profiles publish to   |
| Skill stage      | `@P67.COCO_SKILLS.P67_CLI`             | Stores SKILL.md files; CoCo downloads from here |
| Access control   | `ALLOWED_ROLES` column in registry     | Controls who can discover/fetch the profile     |
| Stage RBAC       | `GRANT READ ON STAGE` to `P67_USER_RL` | Controls who can read skill files from stage    |

### RBAC model (least-privilege)

`P67_USER_RL` gets three grants scoped to only the skill stage:

```sql
GRANT USAGE ON DATABASE P67 TO ROLE P67_USER_RL;           -- enter the building
GRANT USAGE ON SCHEMA P67.COCO_SKILLS TO ROLE P67_USER_RL; -- enter one room
GRANT READ ON STAGE P67.COCO_SKILLS.P67_CLI TO ROLE P67_USER_RL; -- read files
```

They cannot see or access any other schema, table, or object in the P67 database.

## Quick start (for operators)

Prerequisites: `snow` CLI, `cortex` CLI, `python3`, and a `snowhouse` connection in `~/.snowflake/connections.toml` with `P67_ADMIN_RL` + `CORTEX_CODE_MODELING_RL` access.

```bash
cd p67/ops/coco-profile

# Release a new version (bumps patch + publishes)
make release

# Or just publish current version without bumping
make publish

# See all available targets
make help
```

After releasing, tell users to run:
```bash
cortex profile sync p67 -c snowhouse
```

## Required roles

| Task                             | Role needed                     |
| -------------------------------- | ------------------------------- |
| Create/modify schema and stage   | `P67_ADMIN_RL`                  |
| Upload files to stage            | `P67_ADMIN_RL`                  |
| Publish to profile registry      | `CORTEX_CODE_MODELING_RL`       |
| Grant stage access to users      | `P67_ADMIN_RL`                  |
| Grant `P67_USER_RL` to new users | `SECURITYADMIN` (via [Lift ticket](https://lift.snowflake.com/lift?id=sc_cat_item_guide&table=sc_cat_item&sys_id=949d1acf1b880110cef3419ead4bcbf1)) |

## How to update the skill

1. Edit `skills/p67-cli/SKILL.md` (and any templates).

2. Release a new version:

    ```bash
    make release
    ```

    This bumps the patch version in `profile.json`, uploads skill files to stage, publishes to the registry, sets `ALLOWED_ROLES`, and grants RBAC.

3. Tell users to sync:
    ```bash
    cortex profile sync p67 -c snowhouse
    ```

CoCo does NOT auto-update profiles. Users keep whatever version they last fetched until they manually sync.

### Manual publish (without Makefile)

If you need to upload skill files without bumping the version:

```bash
./publish.sh
```

Or upload a single file directly:

```bash
snow sql -q "
  USE ROLE P67_ADMIN_RL;
  USE WAREHOUSE P67_WH;
  PUT 'file://skills/p67-cli/SKILL.md' '@P67.COCO_SKILLS.P67_CLI/skills/p67-cli/' AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
" -c snowhouse
```

### What publish.sh does

1. Creates `P67.COCO_SKILLS` schema and `P67_CLI` stage (idempotent)
2. Uploads SKILL.md and templates to the stage
3. Publishes the profile to `CORTEX_CODE.CONFIG.PROFILE_REGISTRY`
4. Sets `ALLOWED_ROLES` via direct SQL UPDATE (see gotcha below)
5. Grants least-privilege access to `P67_USER_RL`
6. Verifies the profile is in the registry

## Version management

Version is single-sourced from `profile.json` using semver (major.minor.patch). The Makefile provides targets for bumping:

```bash
make version      # show current version
make bump-patch   # 0.1.0 -> 0.1.1
make bump-minor   # 0.1.0 -> 0.2.0
make bump-major   # 0.1.0 -> 1.0.0
make release      # bump-patch + publish (the one-shot)
```

## How to add new users

1. Grant `P67_USER_RL` to the user (requires SECURITYADMIN):

    ```sql
    GRANT ROLE P67_USER_RL TO USER <username>;
    ```

2. Send them the setup script or have them run it from the repo:

    ```bash
    ./p67/ops/coco-profile/setup.sh
    ```

    The script will:
    - Ask whether to create a new snowhouse connection or use an existing one
    - If new: prompt for their Snowflake username and write `[snowhouse]` to `connections.toml`
    - Install the P67 profile and set it as default

    To see who currently has the role:

    ```bash
    ./p67/ops/coco-profile/check-distribution.sh
    ```

## How to remove a user

Revoke the role:

```sql
REVOKE ROLE P67_USER_RL FROM USER <username>;
```

They'll still have a local copy of the profile, but won't be able to sync or fetch updated skills from the stage.

## Gotchas

### `cortex profile publish` ignores `allowedRoles`

The `cortex profile publish --from-file` command does not write the `allowedRoles` field to the registry, regardless of whether it's a string or array in the JSON. The publish script works around this with a direct SQL UPDATE in Step 4b:

```sql
USE ROLE CORTEX_CODE_MODELING_RL;
UPDATE CORTEX_CODE.CONFIG.PROFILE_REGISTRY
SET ALLOWED_ROLES = PARSE_JSON('["P67_USER_RL"]')
WHERE CONFIG_NAME = 'p67';
```

The `allowedRoles` field is kept in `coco-profile.json` as documentation of intent.

### Snowhouse connection needs a warehouse

The `snowhouse` connection in `~/.snowflake/connections.toml` must have a `warehouse` set (e.g., `P67_WH`). Without it, `cortex profile publish` fails with "No active warehouse selected."

### No automatic updates

CoCo fetches the profile once on `cortex profile add` and caches it locally. Updates require users to run `cortex profile sync p67 -c snowhouse`. There is no push mechanism or auto-check.

### Snowsight has no profile support

CoCo in Snowsight (the side panel) does not support profiles. This distribution mechanism only works for CoCo Desktop and CLI.

## Target users

Run `./check-distribution.sh` to see who currently has `P67_USER_RL`.
