# Troubleshooting Agent (DDA)

AI-powered diagnostic troubleshooting agent with integrated Snowflake diagnostic data and Glean search capabilities.

## Overview

The Troubleshooting Agent helps diagnose Snowflake customer issues by combining:
- **DDA Tools**: Direct access to Snowflake diagnostic data (cases, queries, warehouses, TSW diagnostics)
- **Glean Search**: Internal knowledge base search for documentation and code
- **AI Reasoning**: Natural language interface powered by Claude

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          User Query                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │   Agent API      │
                    │  (Port 8002)     │
                    └─────────┬────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │  DDA MCP Server     │   │   Glean Proxy       │
    │   (Port 8000)       │   │   (Port 8006)       │
    │                     │   │   OAuth: 8092       │
    └──────────┬──────────┘   └──────────┬──────────┘
               │                         │
               ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │   Snowflake DB      │   │   Glean API         │
    │   (SUPPORT.CXE)     │   │   (OAuth)           │
    └─────────────────────┘   └─────────────────────┘
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| **fde-dda-service** | 8000 | MCP server providing Snowflake diagnostic tools |
| **glean-proxy** | 8006 | MCP proxy for Glean search and knowledge tools |
| **glean-proxy (OAuth)** | 8092 | OAuth callback for Glean authentication |
| **agent-api** | 8002 | Main agent API endpoint |

## Available DDA Tools

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

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Snowflake account credentials
- Glean access for OAuth authentication

### Setup

1. **Configure environment**:
```bash
cd troubleshooting
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```bash
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=SUPPORT
SNOWFLAKE_SCHEMA=CXE
SNOWFLAKE_WAREHOUSE=DDA_WH
SNOWFLAKE_ROLE=DDA_ROLE
```

2. **Start services**:
```bash
docker compose up
```

This will start all three services:
- DDA MCP Server (port 8000)
- Glean Proxy (port 8006, OAuth on 8092)
- Agent API (port 8002)

3. **Authenticate with Glean**:
   - A browser window will open automatically for OAuth
   - Complete the authentication flow
   - OAuth tokens are persisted in the `glean-tokens` volume

### Usage

#### Using the Agent CLI

```bash
# In a new terminal
docker exec -it dda-agent-api uv run app/agent_cli.py
```

#### Example Queries

```
> Get details for case 01172497

> What queries are running on warehouse COMPUTE_WH?

> Check for lock conflicts in query 01abc-123-456

> Search Glean for documentation about query optimization

> Compare query 01abc-123 with 01def-456
```

#### Using the API

```bash
# Health check
curl http://localhost:8002/health

# Query the agent
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Get details for case 01172497",
    "conversation_id": "test-123"
  }'
```

### Stopping Services

```bash
docker compose down
```

To also remove volumes (OAuth tokens):
```bash
docker compose down -v
```

## Configuration

### Disable Glean Integration

If you only want DDA diagnostic tools (no Glean search):

```yaml
# In docker-compose.yml, remove or comment out:
services:
  glean-proxy:
    # ...entire service
```

And update the agent-api depends_on to remove glean-proxy dependency.

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

## Troubleshooting

### "Connection refused" error
- **Cause**: Services aren't running
- **Solution**: Run `docker compose up` and wait for all services to be healthy

### Glean OAuth fails
- **Cause**: Browser didn't open or OAuth callback failed
- **Solution**:
  ```bash
  docker compose restart glean-proxy
  # Complete OAuth in the browser when it opens
  ```

### "SNOWFLAKE_ACCOUNT not set" error
- **Cause**: Missing environment variables
- **Solution**: Create a `.env` file with required variables (see Setup section)

### Port already in use
- **Cause**: Another docker-compose is using the same ports
- **Solution**:
  ```bash
  # Check what's using the ports
  lsof -i :8000
  lsof -i :8002
  lsof -i :8006

  # Stop conflicting services
  docker ps
  docker stop <container_name>
  ```

### Agent can't find tools
- **Cause**: Services started but not fully initialized
- **Solution**: Wait 10-15 seconds after starting services, check health:
  ```bash
  curl http://localhost:8000/health
  curl http://localhost:8006/health
  curl http://localhost:8002/health
  ```

### View logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f fde-dda-service
docker compose logs -f glean-proxy
docker compose logs -f agent-api
```

## Development

### Running without Docker

```bash
# Terminal 1: Start DDA MCP Server
uv run app/dda_mcp_server.py

# Terminal 2: Start Glean Proxy
uv run app/glean_proxy.py

# Terminal 3: Start Agent API
uv run app/agent_api.py

# Terminal 4: Run CLI
uv run app/agent_cli.py
```

### Running Tests

```bash
uv run pytest
```

## Support

For issues or questions:
1. Check service logs: `docker compose logs -f`
2. Verify environment variables in `.env`
3. Ensure Snowflake credentials have correct permissions
4. Contact the Customer Experience Engineering team
