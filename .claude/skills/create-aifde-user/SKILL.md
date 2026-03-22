---
name: create-aifde-user
description: "Create a new user in the SFENGINEERING.AIFDE Snowflake account. Use when: provisioning users, adding team members to AIFDE, onboarding new users. Triggers: create user, new user, add user, provision user, AIFDE user, onboard user."
---

# Create AIFDE User

Create a new user in the SFENGINEERING.AIFDE Snowflake account using the provisioning scripts in `ops/users/`.

## Prerequisites

- **`snow` CLI** installed (`snow --version`)
- A Snow CLI connection to the AIFDE account with **ACCOUNTADMIN** privilege

## Stopping Points

- **MANDATORY STOPPING POINT** in Step 1: If no saved connection exists, ask the user for their Snow CLI connection name. Do NOT proceed until they respond.
- **MANDATORY CHECKPOINT** before Step 4 (Provision): Present the full YAML config, connection name, and confirm the temporary password. NEVER proceed without explicit user approval.

## Workflow

### Step 1: Check for Saved Connection

Read the saved connection from `.claude/skills/create-aifde-user/local_settings.json`. The file has this format:

```json
{ "connection": "aifde.setli" }
```

- If the file does not exist, ask the user for their Snow CLI connection name for the AIFDE account, then write it to `local_settings.json`.
- If the file exists, display the saved connection and ask if they want to use it or change it.

### Step 2: Collect User Information

Ask the user for:

| Field | Description | Example |
|-------|-------------|---------|
| LDAP username | Snowflake login name | `jsmith` |
| First name | User's first name | `John` |
| Last name | User's last name | `Smith` |
| Email address | Must be `@snowflake.com` | `john.smith@snowflake.com` |

Validate that the email ends with `@snowflake.com`.

### Step 3: Generate YAML Config

Run the following from the repo root to create the user config file:

```bash
cd ops/users && printf '%s\n' "<ldap_username>" "<first_name>" "<last_name>" "<email>" | ./define_user.sh
```

This creates `ops/users/<ldap_username>.yml`. Read it back and show the contents to the user.

If the file already exists, inform the user and ask if they want to proceed with the existing config or abort.

### Step 4: Confirm and Provision

Before provisioning, display:
- The full YAML config
- The connection that will be used
- Remind the user this will run as ACCOUNTADMIN

Ask the user for a **temporary password** to set on the new account.

Then provision the user:

```bash
cd ops/users && CONNECTION=<connection> ./create_user.sh <ldap_username>
```

When prompted for the temp password, provide the value the user gave.

### Step 5: Verify

Run these queries to confirm the user was created correctly:

```sql
SHOW USERS LIKE '<ldap_username>';
```

```sql
SHOW GRANTS TO USER <ldap_username>;
```

Confirm:
- The user exists with the correct `login_name`, `display_name`, `email`
- The `SIADMIN` role is granted
- The `P67_USER_RL` role is granted

Report the results to the user.

## Output

- A new Snowflake user in the AIFDE account with `SIADMIN` and `P67_USER_RL` roles granted
- A YAML config file saved at `ops/users/<username>.yml`
- Saved connection preference in `.claude/skills/create-aifde-user/local_settings.json`

## Reference

### YAML Config Fields

| Field | Default | Description |
|-------|---------|-------------|
| `login_name` | LDAP username | Snowflake login name |
| `display_name` | LDAP username | Display name in Snowflake |
| `first_name` | (prompted) | User's first name |
| `last_name` | (prompted) | User's last name |
| `email` | (prompted) | Email address |
| `must_change_password` | `TRUE` | Force password change on first login |
| `default_warehouse` | `compute_wh` | Default warehouse |
| `default_role` | `public` | Default role |

### SQL Statements Executed

`create_user.sql` runs three statements:

1. `CREATE USER IF NOT EXISTS` with all config fields
2. `GRANT ROLE SIADMIN TO USER`
3. `GRANT ROLE P67_USER_RL TO USER`

### Existing User Configs

User YAML files are stored in `ops/users/*.yml`. You can list them to see who has already been provisioned.

## Troubleshooting

### `snow` CLI not found
Install the Snowflake CLI:
```bash
pip install snowflake-cli-labs
# or
brew install snowflake-cli
```

### Connection error / auth failure
Verify the connection works:
```bash
snow connection test -c <connection>
```
If it fails, re-add the connection:
```bash
snow connection add
```

### User already exists
The SQL uses `CREATE USER IF NOT EXISTS`, so this is safe. The existing user will not be modified, but the `GRANT ROLE` statements will still run (also idempotent).

### ACCOUNTADMIN role not available
The provisioning script runs with `--role ACCOUNTADMIN`. If your connection's user does not have ACCOUNTADMIN, ask an account admin to grant it or to run the provisioning on your behalf.
