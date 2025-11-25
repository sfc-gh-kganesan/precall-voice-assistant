# CXE Copilot - Snowflake Troubleshooting Agent

<div align="center">

```
╔═══════════════════════════════════════════════════╗
║                                                   ║
║            _____ __   __   _____                  ║
║           / ____|\ \ / /  / ____|                 ║
║          | |      \ V /  | |                      ║
║          | |       > <   | |                      ║
║          | |____  / . \  | |____                  ║
║           \_____\/_/ \_\  \_____|                 ║
║                                                   ║
║                  CX Copilot                       ║
║       Your Snowflake troubleshooting AI          ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
```

**AI-powered diagnostic assistant with integrated Snowflake data and enterprise knowledge search**

[🚀 Get Started](#quick-start-full-agent) • [🔧 MCP Server Only](#mcp-server-only) • [📖 Documentation](#available-tools)

</div>

---

## Choose Your Path

### 🎯 Full AI Agent (Recommended)
**Best for: Support engineers, troubleshooting workflows**

Complete AI-powered assistant with natural language interface, combining:
- 🔍 DDA diagnostic tools for Snowflake cases, queries, and warehouses
- 📚 Glean search for internal knowledge base
- 📖 Cortex search for official Snowflake documentation
- 🎫 JIRA integration for ticket search and analysis (optional)
- 🤖 Claude-powered reasoning and analysis

→ [Jump to Full Agent Setup](#quick-start-full-agent)

### 🛠️ MCP Server Only
**Best for: Developers, custom integrations, Claude Desktop users**

Lightweight MCP server exposing DDA diagnostic tools directly:
- Direct access to 20+ diagnostic tools via MCP protocol
- No AI agent overhead
- Easy integration with any MCP client (Claude Desktop, custom apps)
- Single Docker container

→ [Jump to MCP Server Setup](#mcp-server-only)

---

## Full AI Agent

### What You Get

The full troubleshooting agent provides a conversational interface to investigate Snowflake customer issues:

```
User: "Investigate case 01172497 - customer reporting slow queries"
  ↓
Agent analyzes case, pulls query history, checks warehouse utilization
  ↓
Agent searches Glean for similar issues and solutions
  ↓
Agent searches Snowflake docs for relevant optimizations
  ↓
Agent provides comprehensive diagnosis with recommendations
```

**Key Capabilities:**
- Natural language query understanding
- Multi-tool orchestration (calls multiple diagnostic tools automatically)
- Context-aware reasoning across cases, queries, and documentation
- Streaming responses with real-time progress
- Conversation history and memory

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          User Query                         │
└──────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │   Agent API      │
                    │  (Port 8002)     │
                    └─────────┬────────┘
                              │
                 ┌────────────┼────────────┐
                 │            │            │
                 ▼            ▼            ▼
    ┌─────────────────┐  ┌────────────┐  ┌─────────────────┐
    │ DDA MCP Server  │  │  Cortex    │  │  Glean Proxy    │
    │  (Port 8000)    │  │  Search    │  │  (Port 8006)    │
    │                 │  │            │  │  OAuth: 8092    │
    └────────┬────────┘  └─────┬──────┘  └────────┬────────┘
             │                 │                   │
             ▼                 ▼                   ▼
    ┌─────────────────┐  ┌────────────┐  ┌─────────────────┐
    │  Snowflake DB   │  │ Snowflake  │  │   Glean API     │
    │ (SUPPORT.CXE)   │  │  Cortex    │  │   (OAuth)       │
    │                 │  │  Search    │  │                 │
    └─────────────────┘  └────────────┘  └─────────────────┘
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| **agent-api** | 8002 | Main agent API endpoint with streaming support |
| **fde-dda-service** | 8000 | MCP server providing Snowflake diagnostic tools |
| **glean-proxy** | 8006 | MCP proxy for Glean search and knowledge tools |
| **glean-proxy (OAuth)** | 8092 | OAuth callback for Glean authentication |

### Quick Start (Full Agent)

#### Prerequisites

- Docker and Docker Compose
- Snowflake account credentials (SUPPORT database access)
- Glean access for OAuth authentication

#### 1. Configure Environment

```bash
cd troubleshooting
cp .env.example .env
# Edit .env with your credentials
```

**Required environment variables:**
```bash
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=SUPPORT
SNOWFLAKE_SCHEMA=CXE
SNOWFLAKE_WAREHOUSE=DDA_WH
SNOWFLAKE_ROLE=DDA_ROLE
```

#### 2. Start Services

```bash
docker compose up
```

This starts all three services:
- DDA MCP Server (port 8000)
- Glean Proxy (port 8006, OAuth on 8092)
- Agent API (port 8002)

**First-time setup:** A browser window will open for Glean OAuth authentication. Complete the flow to enable knowledge search. OAuth tokens are persisted in the `glean-tokens` volume.

#### 3. Use the Agent

**Option A: Interactive CLI**

```bash
# In a new terminal
docker exec -it dda-agent-api uv run app/interfaces/cli.py
```

The CLI provides a conversational interface with:
- Real-time streaming responses
- Tool call visibility
- Conversation history
- Auto-completion

**Example queries:**
```
> Investigate case 01172497

> What queries are running on warehouse COMPUTE_WH?

> Check for lock conflicts in query 01abc-123-456

> Search for documentation about query optimization

> Compare query 01abc-123 with 01def-456

> Search JIRA for tickets related to case 01172497
```

**Option B: HTTP API**

```bash
# Health check
curl http://localhost:8002/health

# Query the agent (non-streaming)
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Get details for case 01172497",
    "conversation_id": "session-123"
  }'

# Query with streaming (SSE)
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze performance issues in case 01172497",
    "conversation_id": "session-123",
    "stream": true
  }'
```

#### 4. Stop Services

```bash
# Stop services
docker compose down

# Stop and remove volumes (OAuth tokens)
docker compose down -v
```

### Configuration Options

#### Disable Glean Integration

If you only want DDA diagnostic tools (no Glean search):

```yaml
# In docker-compose.yml, remove or comment out:
services:
  glean-proxy:
    # ...entire service
```

And update agent-api `depends_on` to remove the glean-proxy dependency.

#### Exclude Specific Glean Tools

Edit `app/mcp/glean_proxy.py` and update the `EXCLUDED_TOOLS` set:

```python
EXCLUDED_TOOLS = {
    "chat",            # AI-powered analysis tool
    "employee_search", # Employee directory search
}
```

Available Glean tools:
- `chat` - AI-powered analysis and synthesis
- `search` - Search documents and files
- `code_search` - Search internal code repositories
- `employee_search` - Find company employees
- `read_document` - Get full document content by URL

---

## MCP Server Only

### What You Get

The DDA MCP Server exposes Snowflake diagnostic tools via the Model Context Protocol (MCP). This is ideal for:
- Integrating diagnostic tools into Claude Desktop
- Building custom applications with MCP clients
- Lightweight deployments without the full agent stack

**No AI agent, no Glean, just diagnostic tools.**

### Architecture

```
┌──────────────────┐
│   MCP Client     │
│ (Claude Desktop, │
│  custom app)     │
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│ DDA MCP Server  │
│  (Port 8000)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Snowflake DB   │
│ (SUPPORT.CXE)   │
└─────────────────┘
```

### Quick Start (MCP Only)

#### 1. Configure Environment

```bash
cd troubleshooting
cp .env.example .env
# Edit .env with Snowflake credentials (same as above)
```

#### 2. Start MCP Server

**Option A: Using Docker (Recommended)**

```bash
# Create a minimal docker-compose file
docker compose -f docker-compose.mcp-only.yml up
```

See [docker-compose.mcp-only.yml](#docker-composemcp-onlyyml) below for the configuration.

**Option B: Run Directly**

```bash
uv run app/mcp/dda_server.py
```

The server will start on `http://localhost:8000/mcp`

#### 3. Connect from Claude Desktop

Add to your Claude Desktop MCP configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "snowflake-dda": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "fde-dda-service",
        "uv",
        "run",
        "app/mcp/dda_server.py"
      ]
    }
  }
}
```

Or if running locally without Docker:

```json
{
  "mcpServers": {
    "snowflake-dda": {
      "command": "uv",
      "args": ["run", "app/mcp/dda_server.py"],
      "cwd": "/path/to/troubleshooting"
    }
  }
}
```

#### 4. Use in Claude Desktop

Restart Claude Desktop. You'll now have access to all DDA diagnostic tools:

```
You: "Get details for case 01172497"

Claude will use the get_case tool automatically to fetch case information.
```

### docker-compose.mcp-only.yml

Create this file for a minimal MCP-only deployment:

```yaml
version: '3.8'

services:
  fde-dda-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fde-dda-service
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./app:/app/app
    restart: unless-stopped
    command: ["uv", "run", "app/mcp/dda_server.py"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Testing the MCP Server

```bash
# Health check
curl http://localhost:8000/health

# List available tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'

# Call a tool (get_case example)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_case",
      "arguments": {
        "case_number": "01172497"
      }
    },
    "id": 2
  }'
```

---

## Available Tools

Both the full agent and MCP server expose these diagnostic tools:

### Case Operations
- **get_case** - Retrieve case details, queries, and metadata
- **search_cases** - Search cases by account, status, or date range
- **get_case_queries** - List all queries associated with a case

### Query Analysis
- **get_query** - Comprehensive query metadata and performance metrics
- **get_query_historical_runs** - Historical execution data
- **get_concurrent_queries** - Find queries running concurrently
- **get_query_logs** - GS and XP logs for debugging
- **get_query_parameters** - Non-default parameter settings
- **compare_queries** - Side-by-side comparison of two queries

### Warehouse Operations
- **get_warehouse** - Warehouse configuration and status
- **get_warehouse_queries** - Queries executed on a warehouse
- **get_warehouse_utilization** - Resource usage metrics

### TSW Diagnostics
- **check_locks** - Detect lock conflicts and blocking queries
- **check_incidents** - Find related incidents and outages
- **check_compilation** - Analyze compilation failures
- **check_udf** - UDF execution issues
- **check_rbac** - Role-based access control problems
- **check_auth** - Authentication failures
- **check_iceberg** - Iceberg table issues

### Account Operations
- **get_account** - Account metadata and configuration
- **search_accounts** - Find accounts by name or region

### JIRA Integration (Optional)
- **search_jira_by_query_id** - Search JIRA tickets by Snowflake query ID
- **search_jira_by_account** - Search JIRA tickets by account locator
- **search_jira_by_case** - Search JIRA tickets by Salesforce case number
- **search_similar_jira_tickets** - Find similar JIRA tickets based on error messages and metadata
- **get_jira_ticket** - Get a single JIRA ticket by key (e.g., "SNOW-12345")

> **Note:** JIRA integration is optional and disabled by default. Enable by setting `JIRA_ENABLED=true` in your `.env` file and providing JIRA credentials.

### Documentation Search
- **search_snowflake_documentation** - Search official Snowflake documentation via Cortex Search for syntax, features, best practices, and technical specifications

---

## Environment Configuration

### Table/View Mappings

The service automatically routes queries to masked views in dev/local environments to protect customer data:

- **dev/local**: Uses `*_MASKED_V` views for all customer data tables
- **canary/prod**: Uses production tables directly

This is handled automatically by `app/utils/table_mappings.py`.

### Cache Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CACHE_ENABLED` | Enable in-memory caching | true |
| `CACHE_TTL_SECONDS` | Cache TTL in seconds | 900 (15 min) |
| `CACHE_MAX_SIZE` | Max cache entries | 1000 |

### JIRA Integration (Optional)

JIRA integration provides additional tools for searching and retrieving JIRA tickets related to Snowflake issues.

**To enable JIRA integration:**

1. Set the following environment variables in your `.env` file:

```bash
# JIRA Integration
JIRA_ENABLED=true
JIRA_ACCOUNT=snowflakecomputing
JIRA_USER=your.email@snowflake.com
JIRA_API_TOKEN=your_api_token_here
JIRA_PROJECT=SNOW
JIRA_MAX_RESULTS=50
JIRA_CACHE_TTL_SECONDS=300
```

2. Generate a JIRA API token:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Create a new API token
   - Copy the token to `JIRA_API_TOKEN`

**JIRA is disabled by default.** If you don't need JIRA integration, leave `JIRA_ENABLED=false`.

---

## Troubleshooting

### Full Agent Issues

#### "Connection refused" error
- **Cause**: Services aren't running
- **Solution**: Run `docker compose up` and wait for all services to be healthy

#### Glean OAuth fails
- **Cause**: Browser didn't open or OAuth callback failed
- **Solution**:
  ```bash
  docker compose restart glean-proxy
  # Complete OAuth in the browser when it opens
  ```

#### Agent can't find tools
- **Cause**: Services started but not fully initialized
- **Solution**: Wait 10-15 seconds after starting, check health:
  ```bash
  curl http://localhost:8000/health
  curl http://localhost:8006/health
  curl http://localhost:8002/health
  ```

### MCP Server Issues

#### "SNOWFLAKE_ACCOUNT not set" error
- **Cause**: Missing environment variables
- **Solution**: Create a `.env` file with required Snowflake credentials

#### Port already in use
- **Cause**: Another process using port 8000
- **Solution**:
  ```bash
  # Check what's using the port
  lsof -i :8000

  # Stop conflicting services
  docker ps
  docker stop <container_name>
  ```

#### Claude Desktop can't connect
- **Cause**: MCP server not running or config path incorrect
- **Solution**:
  1. Verify server is running: `curl http://localhost:8000/health`
  2. Check Claude Desktop logs: `~/Library/Logs/Claude/mcp*.log`
  3. Verify `cwd` path in config is absolute and correct

### View Logs

```bash
# Full agent - all services
docker compose logs -f

# Full agent - specific service
docker compose logs -f agent-api
docker compose logs -f fde-dda-service
docker compose logs -f glean-proxy

# MCP only
docker compose -f docker-compose.mcp-only.yml logs -f
```

---

## Development

### Running Locally (Full Stack)

```bash
# Terminal 1: Start DDA MCP Server
uv run app/mcp/dda_server.py

# Terminal 2: Start Glean Proxy
uv run app/mcp/glean_proxy.py

# Terminal 3: Start Agent API
uv run app/interfaces/api.py

# Terminal 4: Run CLI
uv run app/interfaces/cli.py
```

### Running Tests

```bash
uv run pytest
```

### Adding New Tools

1. Add tool implementation to `app/tools/`
2. Register in `app/mcp/dda_server.py`
3. Add tests in `tests/`
4. Update tool documentation in this README

---

## Support

For issues or questions:
1. Check service logs: `docker compose logs -f`
2. Verify environment variables in `.env`
3. Ensure Snowflake credentials have correct permissions
4. Contact alejandro.herrera@snowflake.com
