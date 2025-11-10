# DDA Agent - MCP & PydanticAI Integration

This directory contains a PydanticAI agent that uses the DDA service as an MCP (Model Context Protocol) server.

## Architecture

- **MCP Server** (`app/mcp_server.py`): Converts the FastAPI app to an MCP server, exposing all REST endpoints as MCP tools
- **PydanticAI Agent** (`app/agent.py`): AI agent configured to use DDA diagnostic tools
- **CLI Interface** (`app/agent_cli.py`): Interactive command-line interface for natural language queries

## Setup

### 1. Install Dependencies

```bash
cd support-data-agent/dda_service
pip install -e .
```

This installs:
- `fastmcp>=2.11.0` - MCP server framework
- `pydantic-ai>=1.9.1` - AI agent framework
- `openai>=1.0.0` - LLM provider

### 2. Set Environment Variables

```bash
# DDA service configuration (from existing .env)
export SNOWFLAKE_ACCOUNT="..."
export SNOWFLAKE_USER="..."
# ... other Snowflake credentials
```

## Usage

### Running the MCP Server

In one terminal, start the MCP server:

```bash
cd support-data-agent/dda_service
python app/mcp_server.py
```

The server will start at `http://localhost:8000/mcp` and expose ~20 MCP tools including:

**Case Operations:**
- `get_case_{case_number}_cases_get` - Get case metadata
- `get_case_queries_{case_number}_queries_cases_get` - Get queries for a case
- `search_cases_search_cases_cases_get` - Search cases by criteria

**TSW Diagnostics:**
- `analyze_locks_{deployment}_{account_id}_{query_id}_locks_get` - Transaction lock analysis
- `analyze_incidents_{case_number}_incidents_get` - Incident error analysis
- `analyze_compilation_{case_number}_compilation_get` - Query compilation issues
- `analyze_udf_{query_id}_udf_get` - UDF analysis
- `analyze_rbac_{deployment}_{account_id}_{query_id}_rbac_get` - RBAC issues
- `analyze_auth_{deployment}_{account_id}_auth_get` - Authentication (SAML/OAuth)
- `analyze_iceberg_{query_id}_iceberg_get` - Iceberg table issues

**Query, Warehouse, Account Operations:**
- Query metadata and analysis tools
- Warehouse performance tools
- Account information tools

### Running the Agent CLI

In another terminal, start the interactive CLI:

```bash
cd support-data-agent/dda_service
python app/agent_cli.py
```

### Example Interactions

```
> Get details for case 01172497
```

The agent will:
1. Call the `get_case` MCP tool
2. Retrieve case metadata (status, priority, dates, account, etc.)
3. Format and present the results

```
> Analyze transaction locks for query 01c00d3d-0a0c-f195-0196-2e015312a02b in azeastus2prod account 103982
```

The agent will:
1. Call the `analyze_locks` MCP tool with deployment, account_id, and query_id
2. Retrieve lock analysis data
3. Explain the lock duration, blocking queries, and configuration issues

```
> Find open performance cases
```

The agent will:
1. Call the `search_cases` tool with appropriate filters
2. Present a list of matching cases

### Using Different Models

You can use different LLM models:

```bash
# Use Anthropic Claude
python app/agent_cli.py "claude-sonnet-4"

# Use different OpenAI model
python app/agent_cli.py "gpt-4o-mini"
```

## How It Works

### 1. FastAPI → MCP Conversion

The `FastMCP.from_fastapi()` function automatically:
- Parses the OpenAPI schema from the FastAPI app
- Converts each endpoint to an MCP tool
- Generates tool descriptions from endpoint docstrings
- Maps request parameters to tool arguments

### 2. Agent Tool Usage

The PydanticAI agent:
- Receives natural language queries from users
- Decides which MCP tools to call based on the query
- Makes HTTP requests to the MCP server (via MCPServerStreamableHTTP)
- Processes tool responses and formats them for the user

### 3. Example Flow

```
User: "Get details for case 01172497"
  ↓
Agent (LLM): "I need to call the get_case tool with case_number=01172497"
  ↓
PydanticAI → HTTP POST http://localhost:8000/mcp
  ↓
MCP Server → FastAPI endpoint GET /api/v1/cases/01172497
  ↓
FastAPI → Snowflake query execution
  ↓
Response flows back through: Snowflake → FastAPI → MCP → PydanticAI → Agent → User
```

## Development

### Adding New Tools

1. Add new FastAPI endpoints to `app/api/v1/endpoints/`
2. Restart the MCP server
3. New endpoints automatically become MCP tools

### Customizing the Agent

Edit `app/agent.py` to:
- Change the system prompt
- Add custom tool filtering
- Modify agent behavior

### Testing

```bash
# Test MCP server directly
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## Troubleshooting

**"Failed to initialize agent"**
- Ensure MCP server is running (`python app/mcp_server.py`)
- Check `OPENAI_API_KEY` is set
- Verify server URL is correct

**"Tool call failed"**
- Check Snowflake credentials in `.env`
- Verify database connectivity
- Check FastAPI logs for errors

**"Connection refused"**
- MCP server must be running before starting the CLI
- Default URL is `http://localhost:8000/mcp`

## Next Steps

- Add more sophisticated prompts for multi-step diagnostics
- Implement workflow patterns from `docs/demo_flows.md`
- Add memory/conversation history
- Create Streamlit UI for visualization
- Add observability with Logfire
