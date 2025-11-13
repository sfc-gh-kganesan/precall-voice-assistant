# FDE DDA Service

Frontend-Decoupled Diagnostic Data Application (DDA) API Service & Agent

## Overview

This project provides two ways to interact with Snowflake diagnostic data:

1. **FastAPI REST API Service** - Backend service for programmatic access to diagnostic data
2. **DDA Agent with MCP Servers** - AI-powered agent with integrated Glean search capabilities

Both services share the same core business logic and can be used independently or together.

### Key Features

**REST API Service:**
- Frontend-Agnostic REST API (Streamlit, React, CLI tools, etc.)
- Query-First Architecture with 18+ endpoints
- Environment-Based Data Masking for dev/local environments
- In-Memory Caching with 15-minute TTL
- Simple API Key Authentication (OAuth2 + JWT in Phase 2)
- Snowflake Connection Pooling
- Auto-Generated API Documentation at `/api/docs`

**DDA Agent:**
- AI-powered diagnostic troubleshooting
- Integrated Glean search for internal knowledge
- Natural language query interface
- MCP server architecture for tool composition
- Support for cases, queries, warehouses, and TSW diagnostics

## Architecture

### REST API Architecture

```
fde_dda_service/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Pydantic settings
│   ├── dependencies.py         # Dependency injection (auth, etc.)
│   ├── api/v1/endpoints/       # REST API endpoints
│   ├── core/                   # Core modules (database, cache, etc.)
│   ├── services/               # Business logic layer
│   ├── queries/                # SQL query definitions
│   ├── models/                 # Pydantic request/response models
│   └── utils/                  # Utilities (table_mappings, etc.)
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
└── .env.example                # Environment configuration template
```

### Agent Architecture

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

The agent requires two MCP servers:
- **DDA MCP Server** (`app/mcp_server.py`) - Snowflake diagnostic tools
- **Glean Proxy** (`app/glean_proxy.py`) - Glean search and knowledge tools

## Quick Start

Choose your path:
- **Path A**: Run the FastAPI REST API service (for programmatic access)
- **Path B**: Run the DDA Agent with MCP servers (for AI-powered troubleshooting)

### Prerequisites

- **uv must be installed** - Fast Python package installer and resolver ([installation guide](https://github.com/astral-sh/uv))
- Snowflake account credentials
- API key for authentication
- (Path B only) Glean access for OAuth authentication

### Installation

1. **Clone the repository** (if not already in the repo):
```bash
cd /path/to/cxe-dda-streamlit/dda_service
```

2. **Install dependencies**:
```bash
uv sync
```

This will automatically create a virtual environment and install all dependencies.

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your Snowflake credentials and API key
```

Required environment variables:
- `SNOWFLAKE_ACCOUNT`: Your Snowflake account (e.g., "snowhouse")
- `SNOWFLAKE_USER`: Service account username
- `SNOWFLAKE_PASSWORD`: Service account password
- `API_KEY`: Secret key for API authentication
- `ENV`: Environment (local/dev/canary/prod)

---

## Path A: Running the FastAPI REST API Service

### Start the Service

```bash
# Development mode with auto-reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- API Base: `http://localhost:8000`
- Swagger Documentation: `http://localhost:8000/api/docs`
- ReDoc Documentation: `http://localhost:8000/api/redoc`
- OpenAPI Spec: `http://localhost:8000/api/openapi.json`

### Testing the API

```bash
# Health check (no auth required)
curl http://localhost:8000/health

# Get query metadata (requires API key)
curl -H "X-API-Key: your_api_key_here" \
     http://localhost:8000/api/v1/queries/01abc-123
```

### API Usage

#### Authentication

All API endpoints require an API key in the request header:

```bash
X-API-Key: your_api_key_here
```

Example with curl:
```bash
curl -H "X-API-Key: your_api_key_here" \
     http://localhost:8000/api/v1/queries/{query_id}
```

Example with Python:
```python
import requests

headers = {"X-API-Key": "your_api_key_here"}
response = requests.get(
    "http://localhost:8000/api/v1/queries/01abc-123",
    headers=headers
)
data = response.json()
```

#### Available Endpoints

**Query Endpoints (Primary - Fully Implemented)**

- `GET /api/v1/queries/{query_id}` - Get comprehensive query metadata
- `GET /api/v1/queries/{query_id}/historical-runs` - Historical runs
- `GET /api/v1/queries/{query_id}/concurrent` - Concurrent queries
- `GET /api/v1/queries/{query_id}/logs/gs` - Global Services logs
- `GET /api/v1/queries/{query_id}/logs/xp` - Execution Platform logs
- `GET /api/v1/queries/{query_id}/parameters` - Non-default parameters
- `GET /api/v1/queries/{query_id}/incidents` - Related incidents
- `GET /api/v1/queries/{query_id}/parent-child` - Query execution tree
- `GET /api/v1/queries/{query_id}/processing-status` - DDA pipeline status
- `POST /api/v1/queries/adhoc-process` - Trigger adhoc processing
- `POST /api/v1/queries/compare` - Compare two queries
- Additional query operations...

**Other Endpoints (Basic GET operations)**

- `GET /api/v1/accounts/{id}` - Get account metadata
- `GET /api/v1/cases/{id}` - Get case information
- `GET /api/v1/warehouses/{id}` - Get warehouse details
- `GET /api/v1/snowpipes/{id}` - Get snowpipe information
- `GET /api/v1/parameters/{name}` - Get parameter details
- `GET /api/v1/tsw/*` - Troubleshooting workflow endpoints
- `POST /api/v1/search` - Universal search
- `GET /api/v1/landing-page` - Landing page data

Full API documentation available at `/api/docs` when the server is running.

---

## Path B: Running the DDA Agent with MCP Servers

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

#### Terminal 1: Start DDA MCP Server

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

#### Terminal 2: Start Glean Proxy

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

#### Terminal 3: Run the Agent

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

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| DDA MCP Server | `http://localhost:8000/mcp` | Snowflake diagnostic tools |
| Glean Proxy | `http://localhost:8001/mcp` | Glean search & knowledge tools |

### Stopping Services

**Python Script Method:**
Press `Ctrl+C` in the terminal where you ran `start_services.py`

**Bash Script Method:**
Close the terminal windows or press `Ctrl+C` in each

**Manual Method:**
Press `Ctrl+C` in each terminal (Terminal 1 and Terminal 2)

### Configuration

#### Disable Glean Integration

If you only want DDA diagnostic tools (no Glean):

```python
# In app/agent.py
agent = create_dda_agent(glean_proxy_url=None)
```

Or only start the DDA MCP Server (skip Terminal 2).

#### Exclude Specific Glean Tools

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

## Environment Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENV` | Environment (local/dev/canary/prod) | local | No |
| `SNOWFLAKE_ACCOUNT` | Snowflake account name | - | Yes |
| `SNOWFLAKE_USER` | Service account username | - | Yes |
| `SNOWFLAKE_PASSWORD` | Service account password | - | Yes |
| `SNOWFLAKE_WAREHOUSE` | Warehouse name | DDA_WH | No |
| `SNOWFLAKE_DATABASE` | Database name | SUPPORT | No |
| `SNOWFLAKE_SCHEMA` | Schema name | CXE | No |
| `SNOWFLAKE_ROLE` | Role name | DDA_ROLE | No |
| `API_KEY` | API authentication key | - | Yes |
| `CACHE_ENABLED` | Enable in-memory caching | true | No |
| `CACHE_TTL_SECONDS` | Cache TTL in seconds | 900 | No |
| `CACHE_MAX_SIZE` | Max cache entries | 1000 | No |
| `QUERY_TIMEOUT_SECONDS` | Query timeout | 300 | No |
| `MAX_QUERY_RESULTS` | Max result rows | 10000 | No |

### Table/View Mappings

**CRITICAL**: The service automatically routes queries to masked views in dev/local environments to protect customer data.

- **dev/local**: Uses `*_MASKED_V` views for all customer data tables
- **canary/prod**: Uses production tables directly

This is handled automatically by `app/utils/table_mappings.py`.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/test_api/test_queries.py
```

### Code Formatting

```bash
# Format code
uv run black app/

# Lint
uv run flake8 app/

# Type checking
uv run mypy app/
```

### Adding More Tools

To add new diagnostic tools, edit the FastAPI endpoints in `app/api/v1/endpoints/`. They'll automatically be exposed as MCP tools via `mcp_server.py`.

## Deployment

### Docker

```bash
# Build image
docker build -t fde-dda-service:latest .

# Run container
docker run -p 8000:8000 --env-file .env fde-dda-service:latest
```

### Docker Compose (Local Development)

```bash
docker-compose up -d
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests (coming in Phase 4).

## Monitoring

### Health Checks

- `/health` - Basic health check (always returns 200 if service is running)
- `/ready` - Readiness check (checks dependencies)

### Logging

Logs are output to stdout in structured format:
```
2024-01-15 10:30:45 - app.main - INFO - Starting fde-dda-service in local environment
```

### Cache Statistics

Get cache performance metrics:
```bash
# Future endpoint (Phase 2)
curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/admin/cache/stats
```

## Troubleshooting

### REST API Service Issues

**Connection refused**:
- Ensure Snowflake credentials are correct in `.env`
- Check network connectivity to Snowflake
- Verify warehouse/database/schema names

**Authentication failed**:
- Verify `API_KEY` in `.env` matches request header
- Check `X-API-Key` header is properly set

**Query returns empty results**:
- In dev/local, ensure masked views exist for the table
- Check `ENV` variable is set correctly
- Verify query parameters are correct

### Agent Service Issues

**"Connection refused" error**:
- **Cause**: One or both MCP servers aren't running
- **Solution**: Make sure both DDA MCP Server and Glean Proxy are running

**Glean OAuth fails**:
- **Cause**: Browser didn't open or OAuth callback failed
- **Solution**:
  1. Stop the Glean proxy (`Ctrl+C`)
  2. Restart it: `uv run app/glean_proxy.py`
  3. Complete OAuth in the browser when it opens

**"SNOWFLAKE_ACCOUNT not set" error**:
- **Cause**: Missing environment variables
- **Solution**: Create a `.env` file with required variables

**Port already in use**:
- **Cause**: Services are already running or ports are occupied
- **Solution**:
  ```bash
  # Check what's using the ports
  lsof -i :8000
  lsof -i :8001

  # Kill existing processes if needed
  kill <PID>
  ```

**Agent can't find tools**:
- **Cause**: Services started but not fully initialized
- **Solution**: Wait 5-10 seconds after starting services before running the agent

### Logs

View application logs:
```bash
# If running locally
# Logs output to stdout

# If running in Docker
docker logs <container_id>

# If running in Kubernetes
kubectl logs -f deployment/fde-dda-service -n dda
```

## Roadmap

### MVP (Current - Week 1-4)
- ✅ FastAPI foundation
- ✅ Simple API key authentication
- ✅ In-memory caching
- ✅ Snowflake connection pooling
- ✅ Table/view mappings (dev/prod)
- ✅ Query view (full implementation)
- ⏳ Basic endpoints for other views
- ⏳ Docker deployment

### Phase 2 (Post-MVP)
- ⏳ OAuth2 + JWT authentication
- ⏳ Redis distributed caching
- ⏳ Full CRUD operations for all views
- ⏳ JIRA integration
- ⏳ Comprehensive test coverage
- ⏳ Prometheus metrics
- ⏳ Advanced monitoring

## Support

For issues or questions:
1. Check `/api/docs` for API documentation
2. Review logs for error messages
3. Consult `REFACTOR_BACKEND_ONLY.txt` for architecture details
4. Try example workflows in `docs/demo_flows.md` (for agent)
5. Contact the Customer Experience Engineering team

## License

Internal Snowflake project - not for external distribution.
