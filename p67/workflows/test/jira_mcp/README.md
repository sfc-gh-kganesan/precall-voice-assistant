# Jira MCP PoC Workflow

A P67 workflow that connects to Atlassian's remote MCP server as a client, searches Jira issues via JQL, and optionally summarizes them using Cortex Complete.

This is a **proof of concept** demonstrating that P67 workflows can connect to external MCP servers and use their tools programmatically.

## What it does

1. **Connects** to `mcp.atlassian.com` via Streamable HTTP using Basic Auth
2. **Discovers** available MCP tools (Jira, Confluence, JSM, Teamwork Graph)
3. **Resolves** the Atlassian cloudId (required for API token auth)
4. **Searches** Jira issues using a JQL query passed as a parameter
5. **Summarizes** the results using Cortex Complete (requires Snowflake connection config)

## Prerequisites

### 1. Atlassian API Token (Rovo MCP scope)

Create a personal API token at https://id.atlassian.com/manage-profile/security/api-tokens.

**Important:** Select the **Rovo MCP** app scope — not "Jira". The "Jira" scope is for direct REST API access; the MCP server requires its own scope to surface Jira/Confluence tools. Without it, you'll only see `getTeamworkGraph*` tools.

### 2. Snowflake Secrets

Store your credentials as Snowflake secrets:

```sql
CREATE DATABASE IF NOT EXISTS <YOUR_DB>;
CREATE SCHEMA IF NOT EXISTS <YOUR_DB>.SECRETS;

CREATE SECRET <YOUR_DB>.SECRETS.JIRA_API_TOKEN
  TYPE = GENERIC_STRING
  SECRET_STRING = '<your Rovo MCP API token>';

CREATE SECRET <YOUR_DB>.SECRETS.JIRA_EMAIL
  TYPE = GENERIC_STRING
  SECRET_STRING = '<your Atlassian email>';

-- Grant the P67 app access
GRANT USAGE ON DATABASE <YOUR_DB> TO APPLICATION P67;
GRANT USAGE ON SCHEMA <YOUR_DB>.SECRETS TO APPLICATION P67;
GRANT READ ON SECRET <YOUR_DB>.SECRETS.JIRA_API_TOKEN TO APPLICATION P67;
GRANT READ ON SECRET <YOUR_DB>.SECRETS.JIRA_EMAIL TO APPLICATION P67;
```

Then update `manifest.yaml` to reference your secret names.

### 3. External Access Integration (EAI)

The SPCS container needs network access to `mcp.atlassian.com`. Add it to the P67 egress network rule:

```sql
-- Check current hosts
DESCRIBE NETWORK RULE P67_APP_DATA.CONFIGURATION.P67_SNOWFLAKE_EGRESS_EAI_NETWORK_RULE;

-- Add mcp.atlassian.com (include all existing hosts)
ALTER NETWORK RULE P67_APP_DATA.CONFIGURATION.P67_SNOWFLAKE_EGRESS_EAI_NETWORK_RULE
  SET VALUE_LIST = (
    'SFCOGSOPS-SNOWHOUSE_AWS_US_WEST_2.snowflakecomputing.com',
    'api.slack.com',
    'wss-primary.slack.com',
    'slack.com',
    'mcp.atlassian.com'
  );
```

> **Note:** This is a one-off until `mcp.atlassian.com` is added to the EAI callback in `native-app/configure_callbacks.sql`.

## Usage

```bash
# Install dependencies
bun install

# Build
bun run build.js
cp manifest.yaml build/
cd build && zip -r workflow.zip index.js index.js.map manifest.yaml && cd ..

# Deploy
p67 workflow deploy

# Run with default JQL
p67 workflow run -n JIRA_MCP_POC

# Run with custom JQL (avoid '=' in the value — use param file instead)
p67 workflow run -n JIRA_MCP_POC -P params.yaml
```

Example `params.yaml`:
```yaml
jql_query: "project = SNOW AND status = Open ORDER BY created DESC"
```

## Known Limitations

- **Cortex Complete requires a Snowflake connection config** in the manifest (`account`, `token`, etc.) to call `sdk.cortexComplete()`. Without it, the LLM summary step fails gracefully. The Jira search still works.
- **API token auth requires cloudId** — the workflow resolves this automatically via `getAccessibleAtlassianResources`, but it adds a round-trip.
- **`p67 workflow run -p` splits on `=`** — JQL queries containing `=` get truncated. Use `-P params.yaml` instead.

## Architecture

```
P67 Workflow (SPCS container)
  └── @modelcontextprotocol/sdk (MCP Client)
        └── StreamableHTTPClientTransport
              └── https://mcp.atlassian.com/v1/mcp
                    ├── Basic Auth (email:api_token)
                    ├── searchJiraIssuesUsingJql(cloudId, jql)
                    ├── getJiraIssue(cloudId, issueIdOrKey)
                    ├── createJiraIssue(cloudId, ...)
                    └── 37 total tools (Jira + Confluence + JSM + Teamwork Graph)
```
