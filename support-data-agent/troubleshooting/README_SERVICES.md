# Running DDA Agent Services

This guide explains how to start all required services for the DDA Agent with Glean integration.

## Overview

The DDA Agent requires two MCP servers to be running:

1. **DDA MCP Server** (`app/mcp_server.py`) - Provides diagnostic tools for Snowflake troubleshooting
2. **Glean Proxy** (`app/glean_proxy.py`) - Provides Glean search and knowledge management tools

## Quick Start

### Option 1: Automated Startup (Python Script - Recommended)

```bash
cd troubleshooting
python start_services.py
```

This script will:
- Start both MCP servers in background processes
- Open browser for Glean OAuth authentication
- Monitor services and handle graceful shutdown
- Works on macOS, Linux, and Windows

Press `Ctrl+C` to stop all services.

### Option 2: Automated Startup (Bash Script - macOS/Linux)

```bash
cd troubleshooting
./start_services.sh
```

This will open separate terminal windows for each service.

### Option 3: Manual Startup (Full Control)

Follow the instructions below to start each service manually in separate terminals.

---

## Manual Setup Instructions

### Terminal 1: Start DDA MCP Server

```bash
cd troubleshooting
uv run app/mcp_server.py
```

**Expected output:**
```
Starting DDA MCP Server...
Server will be available at http://localhost:8000/mcp

Available tools will include:
  - Case operations (get_case, search_cases, get_case_queries)
  - TSW diagnostics (locks, incidents, compilation, UDF, RBAC, auth, iceberg)
  - Query analysis
  - Warehouse operations
  - Account operations
```

**Keep this terminal running.**

### Terminal 2: Start Glean Proxy

```bash
cd troubleshooting
uv run app/glean_proxy.py
```

**Expected output:**
```
======================================================================
Glean MCP Proxy Server
======================================================================

Connecting to: https://snowflake-be.glean.com/mcp/default
Authentication: OAuth (browser-based)

Starting proxy server...
  Local URL: http://localhost:8001/mcp

Note: A browser window will open for OAuth authentication.
======================================================================
```

**What happens next:**
1. A browser window will open automatically
2. You'll be prompted to authenticate with Glean
3. Complete the OAuth flow in the browser
4. The proxy will confirm connection and list available tools
5. Keep this terminal running

### Terminal 3: Run the Agent

Once both services are running and Glean OAuth is complete:

```bash
cd troubleshooting
uv run app/agent_cli.py
```

**Example queries:**
```
> Get details for case 01172497
> Search for documents about authentication issues
> Find employees working on query optimization
> What tools do you have available?
```

---

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| DDA MCP Server | `http://localhost:8000/mcp` | Snowflake diagnostic tools |
| Glean Proxy | `http://localhost:8001/mcp` | Glean search & knowledge tools |

---

## Stopping Services

### Python Script Method
Press `Ctrl+C` in the terminal where you ran `start_services.py`

### Bash Script Method
Close the terminal windows or press `Ctrl+C` in each

### Manual Method
Press `Ctrl+C` in each terminal (Terminal 1 and Terminal 2)

---

## Troubleshooting

### "Connection refused" error
- **Cause**: One or both MCP servers aren't running
- **Solution**: Make sure both Terminal 1 and Terminal 2 are running their respective services

### Glean OAuth fails
- **Cause**: Browser didn't open or OAuth callback failed
- **Solution**:
  1. Stop the Glean proxy (`Ctrl+C` in Terminal 2)
  2. Restart it: `uv run app/glean_proxy.py`
  3. Complete OAuth in the browser when it opens

### "SNOWFLAKE_ACCOUNT not set" error
- **Cause**: Missing environment variables
- **Solution**: Create a `.env` file with:
  ```
  SNOWFLAKE_ACCOUNT=your_account
  SNOWFLAKE_PASSWORD=your_password
  ```

### Port already in use
- **Cause**: Services are already running or ports are occupied
- **Solution**:
  ```bash
  # Check what's using the ports
  lsof -i :8000
  lsof -i :8001

  # Kill existing processes if needed
  kill <PID>
  ```

### Agent can't find tools
- **Cause**: Services started but not fully initialized
- **Solution**: Wait 5-10 seconds after starting services before running the agent

---

## Configuration

### Disable Glean Integration

If you only want DDA diagnostic tools (no Glean):

```python
# In app/agent.py
agent = create_dda_agent(glean_proxy_url=None)
```

Or only start the DDA MCP Server (skip Terminal 2).

### Exclude Specific Glean Tools

Edit `app/glean_proxy.py` and update the `EXCLUDED_TOOLS` set:

```python
EXCLUDED_TOOLS = {
    "chat",            # AI-powered analysis tool
    "employee_search", # Add more tools to exclude
}
```

Available Glean tools:
- `chat` - AI-powered analysis and synthesis
- `search` - Search documents and files
- `code_search` - Search internal code repositories
- `employee_search` - Find company employees
- `read_document` - Get full document content by URL

---

## Development Notes

### Service Architecture

```
User Query → agent.py (DDA Agent)
                ↓
    ┌───────────┴───────────┐
    ↓                       ↓
DDA MCP Server          Glean Proxy
(localhost:8000)        (localhost:8001)
    ↓                       ↓
Snowflake DB          Glean API (OAuth)
```

### Adding More Tools

To add new diagnostic tools, edit the FastAPI endpoints in `app/api/v1/endpoints/`. They'll automatically be exposed as MCP tools via `mcp_server.py`.

---

## Next Steps

- Review available tools: Ask the agent "What tools do you have?"
- Try example workflows in `docs/demo_flows.md`
- Configure custom prompts in `app/agent.py`
