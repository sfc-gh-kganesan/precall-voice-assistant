---
name: p67-cli
description: "Use the P67 CLI to build, deploy, and run agentic workflows on Snowflake. Use when: creating workflows, deploying to controld, managing secrets, setting up OAuth, viewing logs. Triggers: p67, workflow, deploy workflow, run workflow, p67 init, p67 build, p67 secret, p67 oauth, p67 connection, p67 logs."
tools:
  - bash
---

# P67 CLI

P67 is an agentic workflow platform for Snowflake. The `p67` CLI is the primary interface for authoring, building, deploying, and running workflows against a controld server (locally or on SPCS).

## Prerequisites

- **Node.js** v20+
- **Bun** v1.1+ (CLI runtime)
- A configured P67 connection (`p67 connection list` to check)

If `p67` is not installed, see the install section at the end of this skill.

## Stopping Points

ALWAYS ask the user before:
- Creating a new connection (`p67 connection add`) — need endpoint URL and PAT
- Deploying a workflow (`p67 workflow deploy`) — confirm which build to deploy
- Running a workflow with params (`p67 workflow run -p`) — confirm parameter values
- Setting up OAuth (`p67 oauth connect`) — need provider, client ID, client secret
- Saving secrets (`p67 secret save`) — need the secret value
- Deleting anything (`p67 workflow delete`, `p67 secret delete`, `p67 connection remove`)

## Command Reference

### `p67 init [name]`

Scaffold a new workflow project.

```bash
p67 init myworkflow
p67 init myworkflow --language python
```

| Option | Description |
|--------|-------------|
| `-l, --language <lang>` | `typescript` (default) or `python` |

Creates: `p67.yml` manifest, source files, `package.json` or Python equivalents.

### `p67 build`

Compile and package the workflow into `workflow.zip`.

```bash
cd myworkflow
p67 build
```

Uses `-p, --project <path>` middleware (defaults to current directory). Reads `p67.yml` to determine language and entry point.

Output: `workflow.zip` in the project root.

### `p67 workflow deploy [filePath]`

Upload a built workflow to controld.

```bash
p67 workflow deploy
p67 workflow deploy ./workflow.zip --overwrite
```

| Option | Description |
|--------|-------------|
| `--overwrite` | Replace existing version instead of creating a new one |

Defaults to `./workflow.zip` if `filePath` is omitted.

### `p67 workflow run [workflowId]`

Execute a deployed workflow.

```bash
p67 workflow run --name myworkflow
p67 workflow run <workflowId>
p67 workflow run --name myworkflow -p KEY1=value1 -p KEY2=value2
p67 workflow run --name myworkflow --param_file params.json
```

| Option | Description |
|--------|-------------|
| `-n, --name <name>` | Run latest version by workflow name |
| `-p, --param <key=value>` | Pass parameters (repeatable) |
| `-P, --param_file <path>` | JSON file with parameters |
| `-t, --timeout <seconds>` | Execution timeout |
| `--poll-interval <ms>` | Status polling interval |

### `p67 workflow list`

List all deployed workflows grouped by name.

```bash
p67 workflow list
```

### `p67 workflow runs [workflowId]`

Browse execution history for a workflow.

```bash
p67 workflow runs --name myworkflow
p67 workflow runs --name myworkflow --limit 20
```

| Option | Description |
|--------|-------------|
| `-n, --name <name>` | Filter by workflow name |
| `-l, --limit <n>` | Number of runs to show |

### `p67 workflow versions <name>`

List all deployed versions of a named workflow.

```bash
p67 workflow versions myworkflow
```

### `p67 workflow delete <workflowId>`

Delete a workflow and all its runs and logs.

```bash
p67 workflow delete <workflowId>
p67 workflow delete <workflowId> --yes
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation prompt |

### `p67 connection add [name]`

Register a controld server connection.

```bash
p67 connection add myconn --endpoint http://localhost:3002
p67 connection add prod --endpoint https://controld.snowflakecomputing.app --set-default
```

| Option | Description |
|--------|-------------|
| `-e, --endpoint <url>` | Controld server URL |
| `-p, --pat <token>` | Snowflake PAT (prompted if omitted) |
| `--set-default` | Make this the default connection |

### `p67 connection list`

Show all configured connections.

```bash
p67 connection list
```

### `p67 connection set-default <name>`

Set the default connection used by all commands.

```bash
p67 connection set-default prod
```

### `p67 connection remove <name>`

Remove a saved connection.

```bash
p67 connection remove myconn
p67 connection remove myconn --yes
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation prompt |

### `p67 secret save <name>`

Save a secret to controld. Reads the value from stdin.

```bash
echo "my-api-key" | p67 secret save MY_SECRET
```

### `p67 secret list`

List stored secrets.

```bash
p67 secret list
p67 secret list --all   # include OAuth tokens
```

| Option | Description |
|--------|-------------|
| `--all` | Include OAuth-managed tokens in the list |

### `p67 secret delete <name>`

Delete a stored secret.

```bash
p67 secret delete MY_SECRET
```

### `p67 oauth connect <provider>`

Start an OAuth flow to obtain and store tokens.

```bash
p67 oauth connect github --secret-name GITHUB_TOKEN --client-id <id> --client-secret <secret>
p67 oauth connect google --secret-name GOOGLE_TOKEN --scopes "email,profile"
p67 oauth connect custom --secret-name MY_TOKEN --authorization-url https://auth.example.com/authorize --token-url https://auth.example.com/token
```

| Option | Description |
|--------|-------------|
| `--secret-name <name>` | **Required.** Name to store the token under |
| `--client-id <id>` | OAuth client ID |
| `--client-secret <secret>` | OAuth client secret |
| `--scopes <scopes>` | Comma-separated scopes |
| `--port <port>` | Local callback port |
| `--https` | Use HTTPS for callback |
| `--authorization-url <url>` | Custom authorization endpoint |
| `--token-url <url>` | Custom token endpoint |

Built-in providers: `github`, `google`, `slack`, `microsoft`, `linear`, `custom`.

### `p67 oauth list`

List stored OAuth tokens.

```bash
p67 oauth list
```

### `p67 oauth refresh <name>`

Refresh an OAuth token.

```bash
p67 oauth refresh GITHUB_TOKEN
p67 oauth refresh GITHUB_TOKEN --client-id <id> --client-secret <secret> --force
```

| Option | Description |
|--------|-------------|
| `--client-id <id>` | Override stored client ID |
| `--client-secret <secret>` | Override stored client secret |
| `--force` | Force refresh even if not expired |

### `p67 oauth revoke <name>`

Revoke and delete an OAuth token.

```bash
p67 oauth revoke GITHUB_TOKEN
p67 oauth revoke GITHUB_TOKEN --force
```

| Option | Description |
|--------|-------------|
| `--force` | Skip confirmation |

### `p67 logs list [workflowId]`

View execution logs.

```bash
p67 logs list --run <runId>
p67 logs list <workflowId> --source stderr --limit 50
```

| Option | Description |
|--------|-------------|
| `-r, --run <runId>` | Filter by run ID |
| `-s, --source <source>` | Filter by log source (stdout/stderr) |
| `-l, --limit <n>` | Number of log entries |
| `--offset <n>` | Pagination offset |

### `p67 manifest from-connection [connection-name]`

Bootstrap a `manifest.yaml` from your Snow CLI connections.

```bash
p67 manifest from-connection
p67 manifest from-connection myconn --no-pat
```

| Option | Description |
|--------|-------------|
| `--no-pat` | Skip PAT inclusion in manifest |

Reads `~/.snowflake/connections.toml` and generates a workflow manifest with Snowflake connection details.

### `p67 coco setup`

Install Cortex Code commands for the current project.

```bash
p67 coco setup
```

### `p67 createProjectRoot <directory>`

Create a project root directory with buildflow tooling.

```bash
p67 createProjectRoot my_projects
```

Creates the directory with `buildflow.html`, `workflow_server.py`, and Python environment setup.

## Global Options

| Option | Description |
|--------|-------------|
| `-c, --connection <name>` | Override the default connection for this command |
| `-p, --project <path>` | Override the project directory (for build/init) |
| `--version` | Show CLI version |

## Common Workflows

### First workflow (zero to running)

```bash
p67 init myworkflow --language typescript
cd myworkflow
# edit src/index.ts to implement your workflow logic
p67 build
p67 workflow deploy
p67 workflow run --name myworkflow
```

### Deploy with parameters

```bash
p67 build
p67 workflow deploy --overwrite
p67 workflow run --name myworkflow -p INPUT="hello" -p MODE="fast"
```

### Set up OAuth for HTTP requests

```bash
p67 oauth connect github \
  --secret-name GITHUB_TOKEN \
  --client-id <your-client-id> \
  --client-secret <your-client-secret> \
  --scopes "repo,read:user"
```

The token is stored as a secret and accessible in your workflow via `sdk.getSecret("GITHUB_TOKEN")`.

### Store a secret

```bash
echo "your-api-key-here" | p67 secret save OPENAI_API_KEY
```

Access in workflow code via `sdk.getSecret("OPENAI_API_KEY")`.

### View run results and debug failures

```bash
p67 workflow runs --name myworkflow --limit 5
p67 logs list --run <runId>
p67 logs list --run <runId> --source stderr
```

### Switch between environments

```bash
p67 connection add local --endpoint http://localhost:3002
p67 connection add prod --endpoint https://controld.snowflakecomputing.app --set-default

p67 workflow list -c local
p67 workflow list -c prod
```

## Troubleshooting

### `p67: command not found`
The CLI is not installed or not in `$PATH`. Install:
```bash
cd p67 && make install-cli
```
Or check: `which p67`

### `Connection refused` / `ECONNREFUSED`
controld is not running at the configured endpoint. Check:
```bash
p67 connection list          # verify endpoint URL
curl <endpoint>/api/health   # test connectivity
```

### `p67 build` fails with TypeScript errors
```bash
node --version   # need v20+
bun --version    # need v1.1+
```
Ensure dependencies are installed: `pnpm install` in the workflow directory.

### `p67 workflow deploy` returns 409 Conflict
A workflow with that name and version already exists. Use `--overwrite`:
```bash
p67 workflow deploy --overwrite
```

### `p67 workflow run` hangs or times out
The workflow is taking too long. Check logs:
```bash
p67 logs list --run <runId> --source stderr
```
Increase timeout: `p67 workflow run --name myworkflow --timeout 300`

### OAuth callback fails
Ensure the redirect URI in your OAuth app config matches `http://localhost:<port>/callback` (or `https://` if using `--https`). Default port is 8967.

### Secret not found in workflow
Secrets are scoped to the controld connection. Verify:
```bash
p67 secret list
p67 connection list   # confirm you're on the right connection
```

## Installing the CLI

If `p67` is not installed:

```bash
# From the P67 repo root
pnpm install --filter "@p67/workflow-sdk" --filter "@p67/cli"
pnpm --filter "@p67/workflow-sdk" run build
make clean install -C ./tools/p67-cli
```

The install script prompts for a directory (default `/usr/local/bin`) and creates a symlink.

Requires: Node.js v20+, Bun v1.1+, pnpm v10+.
