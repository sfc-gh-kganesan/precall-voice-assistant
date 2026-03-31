# Using Snowflake Secrets with P67 Workflows

This guide explains how to securely provide credentials, API keys, and other sensitive
values to your P67 workflows using Snowflake's native SECRET objects.

## Overview

P67 workflows often need access to sensitive credentials — API keys, tokens, passwords,
and other secrets. Rather than managing encryption or external secret stores, P67
integrates directly with Snowflake's built-in SECRET objects. Your secrets stay in your
Snowflake account, governed by your existing access controls, and are mounted securely
into workflow containers at runtime.

**Key benefits:**

- Secrets are managed entirely within Snowflake using standard SQL
- Snowflake handles encryption at rest — no custom encryption configuration
- Access is controlled through Snowflake's role-based access control (RBAC)
- P67 never sees or stores your secret values — they are injected directly by the platform
- Secret rotation takes effect on the next workflow run with no redeployment

## Prerequisites

- A P67 application installed in your Snowflake account
- A role with privileges to create secrets (e.g., SYSADMIN or a custom role)
- A database and schema where you want to store your secrets

## Setup

### Step 1: Create a schema for your secrets (recommended)

While you can store secrets in any schema, we recommend creating a dedicated one
to keep your secrets organized and simplify access grants.

```sql
CREATE SCHEMA IF NOT EXISTS MY_DB.SECRETS
  COMMENT = 'Secrets for P67 workflow credentials';
```

### Step 2: Grant the P67 application access to the schema

The P67 application needs USAGE on the database and schema to reference secrets
stored there. These grants do not give P67 access to any tables, views, or other
data — only the ability to reference objects you explicitly grant READ on.

```sql
GRANT USAGE ON DATABASE MY_DB TO APPLICATION P67;
GRANT USAGE ON SCHEMA MY_DB.SECRETS TO APPLICATION P67;
```

> **Note:** These are one-time grants per database/schema. You do not need to
> repeat them for each new secret in the same schema.

## Creating and using secrets

### Step 3: Create a secret

Use the standard Snowflake `CREATE SECRET` command:

```sql
CREATE SECRET MY_DB.SECRETS.OPENAI_API_KEY
  TYPE = GENERIC_STRING
  SECRET_STRING = 'sk-proj-abc123...'
  COMMENT = 'OpenAI API key for my workflow';
```

Snowflake supports several secret types. For most workflow credentials (API keys,
tokens, passwords), use `TYPE = GENERIC_STRING`.

### Step 4: Grant READ to the P67 application

Each secret must be individually granted to the P67 application:

```sql
GRANT READ ON SECRET MY_DB.SECRETS.OPENAI_API_KEY TO APPLICATION P67;
```

> **Security note:** This grant is scoped to this specific secret only. The P67
> application cannot read other secrets in the schema unless you explicitly grant
> them.

### Step 5: Reference the secret in your workflow manifest

In your workflow's `manifest.yaml`, use the fully-qualified secret name
(`DATABASE.SCHEMA.SECRET_NAME`) with the `secretRef` field in the `config` section:

```yaml
name: my-workflow
config:
  - config_name: snowflake
    account:
      value: "MY_ACCOUNT"
    token:
      secretRef: "MY_DB.SECRETS.MY_SNOWFLAKE_TOKEN"
    parameters:
      OPENAI_KEY:
        secretRef: "MY_DB.SECRETS.OPENAI_API_KEY"
```

The `secretRef` field accepts a fully-qualified Snowflake secret name in the format
`DATABASE.SCHEMA.SECRET_NAME`. You can use `secretRef` on connection fields (like
`token`, `password`) or on entries within `parameters` for custom credentials.

### Step 6: Access the secret in your workflow code

**TypeScript:**

```typescript
export async function main(sdk) {
    // Read a secret-backed parameter
    const apiKey = sdk.getParameter('OPENAI_KEY');

    // Use it in your workflow logic
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
        headers: { 'Authorization': `Bearer ${apiKey}` },
        // ...
    });

    return { success: true };
}
```

**Python:**

```python
def main(sdk):
    api_key = sdk.get_parameter('OPENAI_KEY')
    # Use api_key in your workflow logic
    return {"success": True}
```

The secret value is available as a resolved string — your workflow code does not need
to know it came from a Snowflake SECRET object.

## Rotating secrets

To update a secret's value, use `ALTER SECRET`:

```sql
ALTER SECRET MY_DB.SECRETS.OPENAI_API_KEY
  SET SECRET_STRING = 'sk-proj-new-key-456...';
```

The updated value takes effect on the **next workflow run**. No redeployment or
configuration change is needed — the platform reads the current secret value each
time a workflow executes.

## Managing secrets

### List your secrets

```sql
SHOW SECRETS IN SCHEMA MY_DB.SECRETS;
```

### View secret metadata

```sql
DESCRIBE SECRET MY_DB.SECRETS.OPENAI_API_KEY;
```

> **Note:** `DESCRIBE SECRET` shows metadata (name, type, creation date) but never
> exposes the secret value. Snowflake does not provide a SQL command to read back
> the secret string.

### Delete a secret

```sql
DROP SECRET MY_DB.SECRETS.OPENAI_API_KEY;
```

> **Warning:** Any workflow referencing this secret will fail on the next run.
> Update the workflow manifest before dropping the secret.

## Using multiple secrets

A workflow can reference any number of secrets across different databases and schemas:

```yaml
name: multi-secret-workflow
config:
  - config_name: snowflake
    token:
      secretRef: "PROD_DB.CREDENTIALS.SF_TOKEN"
    password:
      secretRef: "PROD_DB.CREDENTIALS.SF_PASSWORD"
    parameters:
      OPENAI_KEY:
        secretRef: "MY_DB.SECRETS.OPENAI_API_KEY"
      SLACK_TOKEN:
        secretRef: "MY_DB.SECRETS.SLACK_BOT_TOKEN"
```

Each secret must have its own `GRANT READ ... TO APPLICATION P67` grant.

## Access control summary

| Grant | Scope | Required | Purpose |
|-------|-------|----------|---------|
| `GRANT USAGE ON DATABASE` | Per database | Once | Allows P67 to reference objects in the database |
| `GRANT USAGE ON SCHEMA` | Per schema | Once | Allows P67 to reference objects in the schema |
| `GRANT READ ON SECRET` | Per secret | Per secret | Allows P67 to read this specific secret value |

The P67 application **cannot**:
- Read secrets without an explicit READ grant
- Access tables, views, or other data in the database/schema (USAGE alone does not grant data access)
- Modify or drop your secrets
- See secret values through metadata commands

## Troubleshooting

### Error: "Database does not exist or not authorized"

The P67 application does not have `USAGE` on the database containing your secret.

```sql
GRANT USAGE ON DATABASE MY_DB TO APPLICATION P67;
```

### Error: "Schema does not exist or not authorized"

The P67 application does not have `USAGE` on the schema containing your secret.

```sql
GRANT USAGE ON SCHEMA MY_DB.SECRETS TO APPLICATION P67;
```

### Error: "Secret not found"

Either:
- The secret name in the manifest does not match the fully-qualified name in Snowflake (check for typos, case sensitivity)
- The secret has not been created yet
- The `secretRef` value is not a three-part name (`DATABASE.SCHEMA.NAME`) — simple names (e.g., `my_secret`) are treated as legacy Postgres-backed secrets, not Snowflake SECRET objects

### Secret value not updating after ALTER SECRET

Verify that:
1. The `ALTER SECRET` command completed successfully
2. You are running a **new** workflow execution (not resuming an existing one)
3. The correct secret name is referenced in the manifest

Each workflow run reads the current secret value at execution time. There is no caching.

## Supported secret types

| Snowflake Secret Type | Use Case | Manifest Field |
|-----------------------|----------|----------------|
| `GENERIC_STRING` | API keys, tokens, passwords | `secretRef` in `config` fields or `config.parameters` |

OAuth-based secrets (`TYPE = OAUTH2`) are not yet supported through `secretRef`.
For OAuth workflows, use the existing `oauthRef` field which handles token refresh
automatically.

## External service tokens (e.g., Atlassian, GitHub)

Workflows can connect to external services using API tokens stored as Snowflake
secrets. A common pattern is storing both an API token and an associated email/username:

```yaml
config:
    - config_name: default
      parameters:
          JIRA_API_TOKEN:
              secretRef: "MY_DB.SECRETS.JIRA_API_TOKEN"
          JIRA_EMAIL:
              secretRef: "MY_DB.SECRETS.JIRA_EMAIL"
```

**Atlassian Rovo MCP note:** When creating an Atlassian API token for use with the
MCP server (`mcp.atlassian.com`), select the **Rovo MCP** app scope — not "Jira".
The "Jira" scope is for direct REST API access; the MCP server requires its own scope
to surface Jira/Confluence tools. Without the correct scope, only Teamwork Graph
read-only tools will be available.

## Migrating from legacy secrets

If you have existing workflows using the legacy P67-managed secret store (simple
secret names like `my_api_key`), you can migrate to Snowflake SECRETs incrementally.
Both secret types work side by side in the same workflow.

### Migration steps per secret

1. Create the Snowflake SECRET with the same value:
   ```sql
   CREATE SECRET MY_DB.SECRETS.MY_API_KEY
     TYPE = GENERIC_STRING
     SECRET_STRING = '<same value as your legacy secret>';
   ```

2. Grant access:
   ```sql
   GRANT USAGE ON DATABASE MY_DB TO APPLICATION P67;
   GRANT USAGE ON SCHEMA MY_DB.SECRETS TO APPLICATION P67;
   GRANT READ ON SECRET MY_DB.SECRETS.MY_API_KEY TO APPLICATION P67;
   ```

3. Update the manifest — change the `secretRef` from a simple name to the
   fully-qualified name:
   ```yaml
   # Before (legacy P67-managed secret)
   parameters:
     API_KEY:
       secretRef: "my_api_key"

   # After (Snowflake SECRET)
   parameters:
     API_KEY:
       secretRef: "MY_DB.SECRETS.MY_API_KEY"
   ```

4. Test the workflow to verify the secret resolves correctly.

5. Optionally delete the legacy secret via `p67 secret delete my_api_key`.

### Mixing secret types

During migration, a single manifest can reference both legacy and Snowflake secrets:

```yaml
config:
  - config_name: snowflake
    token:
      secretRef: "MY_DB.SECRETS.SF_TOKEN"        # Snowflake SECRET (FQN)
    parameters:
      OLD_KEY:
        secretRef: "my_old_key"                    # Legacy (simple name)
      NEW_KEY:
        secretRef: "MY_DB.SECRETS.NEW_KEY"         # Snowflake SECRET (FQN)
```

The system automatically routes each secret to the correct backend based on the
name format:
- **Three-part name** (`DB.SCHEMA.NAME`) → Snowflake SECRET object
- **Simple name** (`my_key`) → Legacy P67-managed store

