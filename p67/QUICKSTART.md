# P67 Quickstart Guide

This guide will help you get started with P67, from setting up the development environment to deploying and running your first workflow.

## Requirements

Before you begin, ensure you have the following installed:

-   **Node.js** (v20 or later)
-   **Bun** (v1.1 or later) - [Install Bun](https://bun.sh/docs/installation)
-   **pnpm** (v10 or later) - `npm install -g pnpm`| [Install pnpm](https://pnpm.io/installation)
-   **Docker** and **Docker Compose** - for running the local development environment

## Setting Up the Development Environment

### 1. Start the Local Services

In one terminal, start the development environment:

```bash
./configure.sh
make dev
```

This will:

-   Start PostgreSQL in Docker
-   Run database migrations
-   Start the controld service
-   Stream logs from all services

Keep this terminal running while developing.

### 2. Build and Install the CLI

In another terminal, build and install the P67 CLI:

```bash
make install-cli
```

You'll be prompted for an install directory:

```
Install directory [/usr/local/bin]:
```

Press **Enter** to accept the default (`/usr/local/bin`), or type a custom path (e.g., `~/.local/bin`).

> **Note:** Ensure the install directory is in your `$PATH`. If it's not, add it to your shell profile (e.g., `~/.zshrc` or `~/.bashrc`):
> ```bash
> export PATH="$PATH:/usr/local/bin"
> ```

### 3. Configure a Connection

Set up a connection to your local controld instance:

```bash
p67 connection add p67 --endpoint http://localhost:3002
```
You will be prompted to enter your Snowflake PAT.

## Your First Workflow

### Step 1: Create a New Workflow Project

```bash
mkdir /tmp/myworkflow
cd /tmp/myworkflow
p67 init
```

This scaffolds a new workflow project with:

-   `manifest.yaml` - Configuration for Snowflake connections and parameters
-   `src/index.ts` - Your workflow code (uses LangGraph)
-   `package.json` - Dependencies

### Step 2: Build the Workflow

```bash
p67 build
```

This compiles your TypeScript code and bundles everything into a deployable package.

### Step 3: Deploy the Workflow

```bash
p67 workflow deploy
```

This uploads your workflow to controld and returns a workflow ID.

### Step 4: Run the Workflow

```bash
p67 workflow run <workflow-id>
```
Workflow ID can be found in returned content from prior command.


Or run the most recently deployed workflow:

```bash
p67 workflow run
```

## Configuring manifest.yaml

The `manifest.yaml` file defines your Snowflake connection(s) and workflow parameters.

### Basic Structure

```yaml
config:
    - config_name: default
      account:
          value: MYORG-MYACCOUNT
      username:
          value: myuser
      token:
          secretRef: snowflake_token # References a secret stored via `p67 secret save`
      warehouse:
          value: MY_WAREHOUSE
      database:
          value: MY_DATABASE
      schema:
          value: PUBLIC
```

### Value Types

Each field can be specified in four ways:

| Type        | Description                           | Example                |
| ----------- | ------------------------------------- | ---------------------- |
| `value`     | Direct inline value                   | `value: MY_DATABASE`   |
| `valueRef`  | Reference to a KV store value         | `valueRef: my_kv_key`  |
| `secretRef` | Reference to an encrypted secret      | `secretRef: my_secret` |
| `oauthRef`  | Reference to an encrypted OAuth token | `oauthRef: my_secret`  |

### Parameters

You can define custom parameters that your workflow can access:

```yaml
config:
    - config_name: default
      # ... connection settings ...
      parameters:
          api_key:
              secretRef: external_api_key
          notification_email:
              value: alerts@example.com
          github_token:
              oauthRef: github_oauth # References an OAuth token
```

Access parameters in your workflow:

```typescript
const apiKey = sdk.getParameter("api_key");
const email = sdk.getParameter("notification_email");
```

### Multiple Configurations

You can define multiple Snowflake configurations for different environments:

```yaml
config:
    - config_name: production
      account:
          value: PROD-ACCOUNT
      # ...

    - config_name: staging
      account:
          value: STAGING-ACCOUNT
      # ...
```

Then specify which config to use in SDK calls:

```typescript
const result = await sdk.executeQueryReadOnly(
    { sqlText: "SELECT * FROM orders" },
    "production" // Use the production config
);
```

## SDK Reference

The WorkflowSDK provides methods for interacting with Snowflake and external services.

### Executing SQL Queries

Run read-only queries against Snowflake:

```typescript
import type { WorkflowSDK } from "./sdk";

export async function main(sdk: WorkflowSDK) {
    const result = await sdk.executeQueryReadOnly({
        sqlText: "SELECT * FROM customers WHERE region = ? LIMIT 10",
        binds: ["US"],
    });

    console.log("Rows:", result.rows);
}
```

**Note:** Only SELECT, WITH, SHOW, and DESCRIBE statements are allowed. DML/DDL operations are blocked for safety.

### Calling Cortex Analyst

Query your data using natural language with Cortex Analyst:

```typescript
export async function main(sdk: WorkflowSDK) {
    const response = await sdk.queryCortexAnalyst(
        "What were the top 5 products by revenue last month?",
        "@my_stage/semantic_model.yaml"
    );

    if (response.success) {
        console.log("Answer:", response.data);
    } else {
        console.error("Error:", response.error);
    }
}
```

### Calling Cortex Agents

Interact with Snowflake Cortex Agents:

```typescript
export async function main(sdk: WorkflowSDK) {
    const response = await sdk.callCortexAgent(
        "Summarize the sales data for Q4",
        {
            agentDatabase: "MY_DB",
            agentSchema: "MY_SCHEMA",
            agentName: "sales_agent",
            onStream: (event) => {
                // Handle streaming events
                console.log(`Event: ${event.eventName}`, event.data);
            },
        }
    );

    if (response.success) {
        console.log("Agent response:", response.data);
    } else {
        console.error("Error:", response.error);
    }
}
```

#### Multi-turn Conversations

Maintain conversation context across multiple calls:

```typescript
// First message
const first = await sdk.callCortexAgent("What were sales last month?", {
    agentName: "sales_agent",
});

// Follow-up using the previous message ID
const followUp = await sdk.callCortexAgent("Break that down by region", {
    agentName: "sales_agent",
    parentMessageId: first.data?.messageId,
});
```

### Making HTTP Requests with OAuth

The SDK supports making authenticated HTTP requests to external APIs using OAuth tokens.

#### Setting Up OAuth

First, connect to an OAuth provider using the CLI:

```bash
# Connect to GitHub (stores token as 'github_oauth')
p67 oauth connect github \
  --secret-name github_oauth \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET \
  --scopes repo,read:user

# Connect to Slack (requires HTTPS)
p67 oauth connect slack \
  --secret-name slack_oauth \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET \
  --port 3000

# Connect to Google
p67 oauth connect google \
  --secret-name google_oauth \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET
```

**Supported providers:** github, google, slack, microsoft, linear, custom

For providers that require HTTPS callbacks (like Slack), the CLI automatically generates a self-signed certificate. You may need to accept the browser security warning.

#### Managing OAuth Tokens

```bash
# List OAuth tokens
p67 oauth list

# Refresh a token (if it has a refresh_token)
p67 oauth refresh github_oauth \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET

# Revoke/delete a token
p67 oauth revoke github_oauth
```

#### Using OAuth in Workflows

Reference the OAuth token in your manifest:

```yaml
config:
    - config_name: default
      parameters:
          github_token:
              oauthRef: github_oauth
```

Then use `httpRequest` with the OAuth reference:

```typescript
export async function main(sdk: WorkflowSDK) {
    // GET request with OAuth - token is automatically injected
    const userResponse = await sdk.httpRequest({
        url: "https://api.github.com/user",
        oauthRef: "github_oauth",
    });

    if (userResponse.success) {
        console.log("GitHub user:", userResponse.data);
    }

    // POST request with body
    const issueResponse = await sdk.httpRequest({
        url: "https://api.github.com/repos/owner/repo/issues",
        method: "POST",
        oauthRef: "github_oauth",
        body: {
            title: "New issue from P67 workflow",
            body: "This issue was created automatically.",
        },
    });

    // Request without OAuth (manual auth)
    const publicResponse = await sdk.httpRequest({
        url: "https://api.example.com/public/data",
        headers: {
            "X-API-Key": sdk.getParameter("api_key"),
        },
    });
}
```

The SDK automatically:

-   Retrieves the OAuth token from secrets
-   Adds the `Authorization: Bearer <token>` header
-   Refreshes expired tokens (when a refresh_token is available)

### Sending Emails

Send emails using Snowflake's email integration:

```typescript
export async function main(sdk: WorkflowSDK) {
    const sent = await sdk.email({
        email_addresses: ["recipient@example.com"],
        subject: "Workflow Complete",
        body: "Your workflow has finished processing.",
        content_type: "text/plain",
    });

    if (sent) {
        console.log("Email sent successfully");
    }
}
```

### Human-in-the-Loop (HITL) Interrupts

Pause workflow execution and wait for human input before continuing. This is useful for approval workflows, collecting user input, or any scenario requiring human decision-making.

#### Basic Usage

```typescript
export async function main(sdk: WorkflowSDK) {
    // Pause and wait for human approval
    const approved = await sdk.interrupt({
        question: "Approve this action?",
        details: { amount: 50000, recipient: "vendor@example.com" }
    });

    if (approved) {
        console.log("Action approved, proceeding...");
        // Continue with the approved action
    } else {
        console.log("Action rejected");
    }
}
```

#### With Timeout

```typescript
export async function main(sdk: WorkflowSDK) {
    try {
        // Wait up to 5 minutes for human input
        const response = await sdk.interrupt<string>(
            { type: "input", prompt: "What city are you in?" },
            { timeout: 300000 } // 5 minutes in milliseconds
        );
        console.log(`User is in: ${response}`);
    } catch (error) {
        console.log("Timed out waiting for input");
    }
}
```

#### Resuming Interrupts via API

When a workflow hits an interrupt, it pauses and the run returns with status `interrupted`. You can then resume it via the API:

```bash
# List pending interrupts
curl http://localhost:3002/api/workflow/interrupts?status=Pending

# Get details of a specific interrupt
curl http://localhost:3002/api/workflow/interrupts/<interrupt-id>

# Resume the interrupt with a response
curl -X POST http://localhost:3002/api/workflow/interrupts/<interrupt-id>/resume \
  -H "Content-Type: application/json" \
  -d '{"response": true}'
```

The `response` value in the resume request becomes the return value of the `sdk.interrupt()` call in your workflow.

#### Interrupt Options

| Option    | Type     | Description                                      |
| --------- | -------- | ------------------------------------------------ |
| `timeout` | `number` | Timeout in milliseconds (default: no timeout)    |
| `nodeId`  | `string` | Optional node identifier for debugging/filtering |

## Managing Secrets

Store sensitive values securely:

```bash
# Save a secret (reads from stdin)
echo "my-api-key-value" | p67 secret save my_api_key

# List secrets
p67 secret list

# Delete a secret
p67 secret delete my_api_key
```

Reference secrets in your manifest using `secretRef`:

```yaml
parameters:
    api_key:
        secretRef: my_api_key
```

## Next Steps

-   Explore the `examples/` directory for more workflow patterns
-   Check out the [LangGraph documentation](https://langchain-ai.github.io/langgraph/) for advanced graph patterns
-   Learn about [Cortex Analyst](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst) and [Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
