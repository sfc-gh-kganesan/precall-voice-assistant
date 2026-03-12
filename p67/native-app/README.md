# Project 67

A workflow orchestration platform that runs inside Snowflake as a Native App with SPCS.

After installation, configure settings according to the prompts in the app UI inside of Snowsight.

## Required References

The following references are **required** during installation. Snowsight will prompt you to bind them:

| Reference                    | Type                        | Purpose                                                                        |
| ---------------------------- | --------------------------- | ------------------------------------------------------------------------------ |
| `google_oauth_eai`           | External Access Integration | Egress to `oauth2.googleapis.com`, `accounts.google.com`, `www.googleapis.com` |
| `google_oauth_client_id`     | Secret (GENERIC_STRING)     | Google OAuth2 Client ID                                                        |
| `google_oauth_client_secret` | Secret (GENERIC_STRING)     | Google OAuth2 Client Secret                                                    |
| `snowflake_egress_eai`       | External Access Integration | Egress to your Snowflake account hostname and Slack APIs                       |
| `postgres_eai`               | External Access Integration | Egress to your Snowflake Postgres instance                                     |
| `postgres_connection_url`    | Secret (GENERIC_STRING)     | Postgres connection URL (includes credentials)                                 |
| `encryption_key`             | Secret (GENERIC_STRING)     | Base64-encoded 32-byte AES-256 key for encrypting user secrets at rest         |

To generate an encryption key:

```sql
SELECT BASE64_ENCODE(RANDSTR(32, RANDOM()));
```

**Important**: The `snowflake_egress_eai` network rule must include Slack API hosts if you plan to use the Slack integration. When prompted to configure this EAI during setup, make sure the following hosts are included: `api.slack.com`, `wss-primary.slack.com`, `slack.com` (in addition to your Snowflake account hostname).

## Slack Integration (Optional)

Slack integration enables running workflows from Slack slash commands and receiving human-in-the-loop (HITL) interrupt notifications as interactive messages with Approve/Reject buttons.

### Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App** > **From scratch**
2. Name it (e.g., "P67 Workflows") and select your workspace

### Step 2: Configure Bot Permissions

Go to **OAuth & Permissions** and add these **Bot Token Scopes**:

| Scope               | Used For                                                    |
| ------------------- | ----------------------------------------------------------- |
| `chat:write`        | Posting workflow status updates and HITL interrupt messages |
| `chat:write.public` | Posting to channels the bot hasn't been invited to          |
| `reactions:write`   | Adding status emoji reactions to workflow messages          |
| `reactions:read`    | Reading reactions (for cleanup)                             |
| `commands`          | Receiving `/workflow` slash commands                        |

### Step 3: Create the Slash Command

Go to **Slash Commands** and click **Create New Command**:

- **Command**: `/workflow`
- **Request URL**: `https://<YOUR_INGRESS_URL>/api/webhook/slack/commands`
- **Short Description**: Run and manage P67 workflows
- **Usage Hint**: `run <id> | list | status <run-id> | link | help`

To get your ingress URL after the app is installed:

```sql
CALL p67.v1.app_url();
```

### Step 4: Enable Interactivity

Go to **Interactivity & Shortcuts** and toggle **Interactivity** on:

- **Request URL**: `https://<YOUR_INGRESS_URL>/api/webhook/slack/interactions`

This is how Slack delivers button clicks (Approve/Reject) from HITL interrupt messages back to P67.

### Step 5: Enable Socket Mode (Optional)

Socket Mode allows P67 to receive events via outbound WebSocket instead of inbound webhooks. This is useful if you prefer not to expose webhook URLs.

1. Go to **Settings** > **Socket Mode** and toggle it on
2. Generate an **App-Level Token** with the `connections:write` scope
3. Save the `xapp-...` token for the next step

If you skip this step, P67 will use webhook mode (Steps 3-4) which works without Socket Mode.

### Step 6: Install the App to Your Workspace

Go to **Install App** and click **Install to Workspace**. After authorization, note the **Bot User OAuth Token** (`xoxb-...`).

Also go to **Basic Information** > **App Credentials** and note the **Signing Secret**.

### Step 7: Create Snowflake Secrets

```sql
CREATE SECRET p67_slack_bot_token
    TYPE = GENERIC_STRING
    SECRET_STRING = 'xoxb-your-bot-token-here';

CREATE SECRET p67_slack_signing_secret
    TYPE = GENERIC_STRING
    SECRET_STRING = 'your-signing-secret-here';

-- Only needed if you enabled Socket Mode in Step 5
CREATE SECRET p67_slack_app_token
    TYPE = GENERIC_STRING
    SECRET_STRING = 'xapp-your-app-token-here';
```

### Step 8: Add Slack Hosts to the Egress Network Rule

Slack egress is handled by the `snowflake_egress_eai` integration. Ensure the network rule for that EAI includes the Slack hosts:

```sql
-- Add Slack hosts to the existing egress network rule.
-- Replace YOUR_SNOWFLAKE_ACCOUNT_HOST with your account hostname.
ALTER NETWORK RULE your_egress_network_rule
    SET VALUE_LIST = (
        'YOUR_SNOWFLAKE_ACCOUNT_HOST.snowflakecomputing.com',
        'api.slack.com',
        'wss-primary.slack.com',
        'slack.com'
    );
```

If the EAI was created through Snowsight's setup prompts, you can find its network rule with:

```sql
DESCRIBE EXTERNAL ACCESS INTEGRATION <your_egress_eai_name>;
-- Then:
DESCRIBE NETWORK RULE <rule_from_above>;
```

After updating the network rule, you may need to recreate the EAI and rebind the `snowflake_egress_eai` reference for the change to take effect (see Troubleshooting).

### Step 9: Bind Slack Secret References

```sql
CALL p67.v1.register_reference('slack_bot_token', 'ADD',
    SYSTEM$REFERENCE('SECRET', 'p67_slack_bot_token', 'PERSISTENT', 'READ'));

CALL p67.v1.register_reference('slack_signing_secret', 'ADD',
    SYSTEM$REFERENCE('SECRET', 'p67_slack_signing_secret', 'PERSISTENT', 'READ'));

-- Only if using Socket Mode
CALL p67.v1.register_reference('slack_app_token', 'ADD',
    SYSTEM$REFERENCE('SECRET', 'p67_slack_app_token', 'PERSISTENT', 'READ'));
```

### Step 10: Reinitialize the Service

```sql
CALL p67.v1.init();
```

This restarts the controld service with the Slack configuration. Check the logs to confirm:

```sql
SELECT SYSTEM$GET_SERVICE_LOGS('p67.app.controld', '0', 'controld', 50);
-- Look for: "Slack Socket Mode connected" and "Slack Bot Token configured"
```

### Step 11: Link Your Slack Account

In Slack, run:

```
/workflow link
```

This connects your Slack user to your P67 account so workflows run under your identity.

### Slack Commands Reference

| Command                              | Description                                 |
| ------------------------------------ | ------------------------------------------- |
| `/workflow run <id> [key=value ...]` | Run a workflow with optional parameters     |
| `/workflow list`                     | List all workflows you have access to       |
| `/workflow status <run-id>`          | Check the status of a workflow run          |
| `/workflow link`                     | Link your Slack account to your P67 account |
| `/workflow help`                     | Show available commands                     |

## Useful Procedures

```sql
CALL p67.v1.app_url();          -- Get the controld ingress URL
CALL p67.v1.dashboard_url();    -- Get the dashboard ingress URL
CALL p67.v1.init();             -- Reinitialize services after config changes
CALL p67.app.stop_app();        -- Stop all services
```

## Troubleshooting

Check service logs:

```sql
SELECT SYSTEM$GET_SERVICE_LOGS('p67.app.controld', '0', 'controld', 100);
SELECT SYSTEM$GET_SERVICE_LOGS('p67.app.dashboard', '0', 'dashboard', 100);
```

Check service status:

```sql
SELECT SYSTEM$GET_SERVICE_STATUS('p67.app.controld');
SELECT SYSTEM$GET_SERVICE_STATUS('p67.app.dashboard');
```

### EAI Reference Invalidation

If you `CREATE OR REPLACE` an External Access Integration, all `SYSTEM$REFERENCE` persistent bindings to that EAI become stale. After replacing an EAI you must:

1. Rebind the reference:
    ```sql
    CALL p67.v1.register_reference('snowflake_egress_eai', 'ADD',
        SYSTEM$REFERENCE('EXTERNAL_ACCESS_INTEGRATION', 'your_eai_name', 'PERSISTENT', 'USAGE'));
    ```
2. Recreate the service (ALTER SERVICE alone is not sufficient):
    ```sql
    CALL p67.app.stop_app();
    CALL p67.v1.create_services(ARRAY_CONSTRUCT('CREATE COMPUTE POOL'));
    CALL p67.v1.init();
    ```

To avoid this, prefer `ALTER EXTERNAL ACCESS INTEGRATION ... SET ALLOWED_NETWORK_RULES` over `CREATE OR REPLACE`.
