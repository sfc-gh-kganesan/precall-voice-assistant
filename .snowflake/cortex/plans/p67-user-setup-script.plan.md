---
name: "p67 user setup script"
created: "2026-03-18T21:08:38.519Z"
status: pending
---

# Plan: P67 User Setup Script

## What

Create `p67/ops/coco-profile/setup.sh` -- a script we send to P67 users that bootstraps everything they need in one shot.

## Script Flow

```
setup.sh
  1. Check cortex CLI is installed
  2. Prompt for Snowflake username (e.g. "VB")
  3. Ensure ~/.snowflake/connections.toml exists
  4. Add [snowhouse] connection if missing (skip if already present)
  5. cortex profile add p67 -c snowhouse
  6. cortex profile set-default p67
  7. Print success + next steps
```

## Connection Config Written

Based on \~/.snowflake/connections.toml, the script will append:

```
[snowhouse]
account = "SFCOGSOPS-SNOWHOUSE_AWS_US_WEST_2"
user = "<prompted>"
authenticator = "externalbrowser"
role = "ENGINEER"
warehouse = "P67_WH"
```

If `[snowhouse]` already exists in their file, the script skips this step and prints a notice.

## Edge Cases

- **No `~/.snowflake/` dir**: script creates it
- **No `connections.toml`**: script creates the file with just the snowhouse block
- **`[snowhouse]` already exists**: skip, don't clobber -- user may have custom settings
- **No `cortex` CLI**: exit with install instructions
- **User already has profile**: `cortex profile add` is idempotent, safe to re-run

## File Changes

1. **Create** p67/ops/coco-profile/setup.sh
2. **Update** p67/ops/coco-profile/README.md -- add "User setup" section pointing to the script

## Usage

We send the user this one-liner or have them clone the repo and run:

```
./p67/ops/coco-profile/setup.sh
```

Or we can distribute the script standalone (it has no dependencies on other repo files).
