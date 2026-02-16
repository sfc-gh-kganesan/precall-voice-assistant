# Slack Slash Command Integration

This document describes how to set up and use Slack slash commands to trigger P67 workflows.

## Overview

P67 supports triggering workflows directly from Slack using slash commands. Users can run workflows, check status, and manage their account linking—all without leaving Slack.

### Supported Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/workflow run <id> [params]` | Run a workflow with optional parameters | `/workflow run data-pipeline customer=acme` |
| `/workflow list` | List all workflows you have access to | `/workflow list` |
| `/workflow status <run-id>` | Check the status of a workflow run | `/workflow status abc-123` |
| `/workflow link` | Link your Slack account to P67 | `/workflow link` |
| `/workflow help` | Show available commands | `/workflow help` |

## Architecture

P67 supports two methods for receiving Slack slash commands:

1. **Socket Mode** (recommended) - Uses WebSocket connection, no public URL required
2. **HTTP Webhook** - Traditional webhook endpoint, requires public URL

Both methods can be enabled simultaneously for redundancy.

## Setup Guide

### Prerequisites

- A Slack workspace where you have permission to create apps
- P67 controld service running and accessible
- Database migration applied (for SlackUser table)

### Step 1: Apply Database Migration

The Slack integration requires a new `SlackUser` table to link Slack accounts to P67 users.

```bash
cd packages/db
pnpm prisma migrate dev --name add_slack_user
```

### Step 2: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name your app (e.g., "P67 Workflows") and select your workspace
4. Click **Create App**

### Step 3: Configure Slash Command

1. In your Slack app settings, go to **Slash Commands**
2. Click **Create New Command**
3. Configure the command:
   - **Command**: `/workflow`
   - **Request URL**: `https://your-controld-url/webhook/slack/commands` (only needed for HTTP mode)
   - **Short Description**: "Run and manage P67 workflows"
   - **Usage Hint**: `run <workflow-id> | list | status <run-id> | link | help`
4. Click **Save**

### Step 4: Enable Socket Mode (Recommended)

Socket Mode eliminates the need for a public URL.

1. Go to **Socket Mode** in app settings
2. Toggle **Enable Socket Mode** to On
3. Create an app-level token:
   - Token Name: `p67-socket`
   - Scope: `connections:write`
4. Copy the token (starts with `xapp-`)
5. Set the environment variable:
   ```bash
   export SLACK_APP_TOKEN=xapp-1-...
   ```

### Step 5: Configure Interactivity (for workflow interrupts)

If your workflows use human-in-the-loop interrupts with Slack buttons:

1. Go to **Interactivity & Shortcuts**
2. Toggle **Interactivity** to On
3. Set **Request URL**: `https://your-controld-url/webhook/slack/interactions`
4. Click **Save Changes**

### Step 6: Set OAuth Scopes

1. Go to **OAuth & Permissions**
2. Under **Scopes** → **Bot Token Scopes**, add:
   - `commands` - For slash commands
   - `chat:write` - For sending messages
   - `reactions:write` - For adding status reactions to messages
3. Click **Install to Workspace** and authorize

### Step 7: Get Bot Token

1. Go to **OAuth & Permissions**
2. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
3. Set the environment variable:
   ```bash
   export SLACK_BOT_TOKEN=xoxb-your-bot-token
   ```

### Step 8: Configure Signing Secret (for HTTP mode)

If using HTTP webhooks (not Socket Mode):

1. Go to **Basic Information**
2. Find **Signing Secret** under App Credentials
3. Set the environment variable:
   ```bash
   export SLACK_SIGNING_SECRET=your-signing-secret
   ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_APP_TOKEN` | For Socket Mode | App-level token starting with `xapp-` |
| `SLACK_BOT_TOKEN` | For threaded messages | Bot User OAuth Token starting with `xoxb-` |
| `SLACK_SIGNING_SECRET` | For HTTP mode | Used to verify requests are from Slack |
| `P67_WEB_URL` | Optional | Base URL for account linking (default: `http://localhost:5173`) |

> **Note**: `SLACK_BOT_TOKEN` is required for workflow run output to appear in Slack threads. Without it, workflows will still run but output won't be posted to Slack.

## Account Linking

Before users can run workflows from Slack, they must link their Slack account to their P67 account.

### Linking Flow

1. User runs `/workflow link` in Slack
2. P67 responds with a unique link URL
3. User clicks the URL and authenticates with P67
4. The accounts are linked
5. User can now run workflows from Slack

### How It Works

- A temporary token is generated and stored in memory (expires in 10 minutes)
- The link URL includes the token and Slack user/team IDs
- When the user authenticates with P67, the endpoint validates the token and creates the `SlackUser` record
- The Slack user ID is mapped to the P67 user ID

## Usage Examples

### Running a Workflow

```
/workflow run my-etl-pipeline
```

With parameters:
```
/workflow run data-export format=csv customer=acme date=2024-01-15
```

### Checking Workflow Status

```
/workflow status 550e8400-e29b-41d4-a716-446655440000
```

### Listing Available Workflows

```
/workflow list
```

## Response Behavior

### Immediate Response

Slack requires a response within 3 seconds. P67 immediately acknowledges the command with a status message:

```
⏳ Starting workflow `data-pipeline`...
```

### Async Updates

For long-running workflows, P67 sends follow-up messages via Slack's `response_url`:

```
✅ Workflow completed successfully (run: `abc-123`)
```

Or if the workflow fails:
```
❌ Workflow failed: Connection timeout
```

### Workflow Interrupts

If a workflow pauses for human input, P67 sends interactive buttons:

```
⏸️ Workflow paused - awaiting input

[Approve] [Reject] [Skip]
```

Clicking a button resumes the workflow with the selected response.

## Troubleshooting

### "Your Slack account is not linked to P67"

Run `/workflow link` to connect your Slack account.

### "Workflow not found or you don't have access"

- Verify the workflow ID is correct
- Ensure the workflow is either owned by you or has `Public` visibility
- Check that your Slack account is linked to the correct P67 user

### Commands not working at all

1. Check that the Slack app is installed to your workspace
2. Verify environment variables are set correctly
3. Check controld logs for errors:
   ```bash
   docker compose logs -f controld
   ```

### Socket Mode not connecting

- Verify `SLACK_APP_TOKEN` is set and starts with `xapp-`
- Check that Socket Mode is enabled in Slack app settings
- Look for connection status in logs: `✅ Slack Socket Mode connected`

### HTTP webhook returning 401

- Verify `SLACK_SIGNING_SECRET` matches your app's signing secret
- Ensure the request timestamp is within 5 minutes (clock sync issues)

## Security Considerations

### Request Verification

All HTTP webhook requests are verified using Slack's signing secret to prevent spoofing. The verification:

1. Checks the `x-slack-request-timestamp` header is within 5 minutes
2. Computes HMAC-SHA256 of the request body
3. Uses constant-time comparison to prevent timing attacks

### Account Linking

- Link tokens expire after 10 minutes
- Tokens are single-use and deleted after successful linking
- The link endpoint requires P67 authentication

### Workflow Access Control

- Users can only run workflows they own or that are marked as `Public`
- The P67 user ID from the linked account is used for authorization
- All workflow runs are logged with the associated user

## Development

### Local Testing with ngrok

For HTTP webhook testing without Socket Mode:

```bash
# Start ngrok tunnel
ngrok http 3002

# Set the webhook URL in Slack app settings to:
# https://abc123.ngrok.io/webhook/slack/commands
```

### Testing Socket Mode

Socket Mode works without a public URL, making local development easier:

```bash
# Set the app token
export SLACK_APP_TOKEN=xapp-1-...

# Start controld
pnpm --filter @p67/controld dev
```

You should see in the logs:
```
🔌 Slack Socket Mode service started
✅ Slack Socket Mode connected
```

## API Reference

### HTTP Endpoints

#### POST `/webhook/slack/commands`

Receives slash command payloads from Slack.

**Request Body** (form-encoded):
- `command` - The slash command (e.g., `/workflow`)
- `text` - Text after the command
- `user_id` - Slack user ID
- `team_id` - Slack workspace ID
- `channel_id` - Channel ID
- `response_url` - URL for async responses

**Response**:
```json
{
  "response_type": "ephemeral",
  "text": "⏳ Starting workflow..."
}
```

#### POST `/webhook/slack/interactions`

Receives interactive component payloads (button clicks).

#### POST `/api/auth/slack/link`

Completes account linking after user authentication.

**Query Parameters**:
- `token` - Link token from `/workflow link`
- `slack_user` - Slack user ID
- `slack_team` - Slack team ID

**Response**:
```json
{
  "success": true,
  "message": "Your Slack account has been linked successfully!"
}
```
