# Testing AgentSim with Snowflake Cortex

This guide explains how to test AgentSim with a real Snowflake Cortex agent that combines LLM capabilities with database query functionality via Cortex Analyst.

## Overview

The Cortex integration uses:
- **Cortex LLM** (Claude 4 Sonnet) for conversational AI
- **Cortex Analyst** for natural language to SQL conversion
- **Pydantic AI** framework for agent orchestration
- **FastAPI** wrapper to expose a compatible endpoint for AgentSim

## Prerequisites

1. **Snowflake Account** with:
   - Cortex LLM access
   - Cortex Analyst access
   - A configured semantic model for your data

2. **Snowflake Credentials** configured in `.env`:
   ```bash
   SNOWFLAKE_ACCOUNT=your_account
   SNOWFLAKE_USER=your_user
   SNOWFLAKE_PASSWORD=your_password_or_token
   SNOWFLAKE_ROLE=your_role
   SNOWFLAKE_WAREHOUSE=your_warehouse
   SNOWFLAKE_DATABASE=your_database
   SNOWFLAKE_SCHEMA=your_schema
   SEMANTIC_MODEL_FILE=@YOUR_STAGE/your_semantic_model.yaml
   ```

3. **Dependencies installed**:
   ```bash
   uv sync
   ```

## Quick Start

Run the end-to-end test:

```bash
uv run test_cortex_e2e.py
```

This will:
1. Start the Cortex wrapper agent (port 8002)
2. Start AgentSim API (port 8000)
3. Create a project pointing to the Cortex agent
4. Run 3 simulation scenarios
5. Display results

## Expected Output

```
🚀 Starting Cortex agent wrapper on port 8002...
🚀 Starting AgentSim API server on port 8000...

⏳ Waiting for servers to be ready...
✅ Cortex agent is healthy at http://localhost:8002
✅ AgentSim API is healthy at http://localhost:8000

📋 Creating test project...
✅ Created project with ID: 1

🔬 Starting simulation...
✅ Started simulation with ID: 1
   Status: pending

⏳ Waiting for simulation to complete...
   (This may take a while as Cortex processes queries)
   Status: running
   Status: completed

✅ Simulation completed successfully!

📊 Fetching results...

============================================================
CORTEX SIMULATION RESULTS
============================================================
Simulation ID: 1
Project ID: 1
Total Simulations: 3
Status: completed
Successful: 3
Failed: 0
Success Rate: 100.0%

Aggregate Metrics:
  avg_turns: 2.33
  avg_duration_ms: 4532.50
  success_rate: 1.00
============================================================

✅ End-to-end Cortex test completed!
```

## Manual Testing

### 1. Start Cortex Wrapper Agent

```bash
uv run python cortex_wrapper_agent.py
```

The agent will:
- Connect to Snowflake
- Initialize Cortex LLM (Claude)
- Register the Cortex Analyst tool
- Start listening on port 8002

### 2. Test Cortex Agent Directly

```bash
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many support cases were opened last week?",
    "conversation_id": "test-123"
  }'
```

### 3. Use with AgentSim

1. Start AgentSim API:
   ```bash
   uvicorn backend.main:app --reload
   ```

2. Create a project via API:
   ```bash
   curl -X POST http://localhost:8000/api/projects/ \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Cortex Test",
       "description": "Testing Cortex agent",
       "business_context": "Customer support data analyst with database access",
       "agent_endpoint": "http://localhost:8002/api/chat",
       "auth_type": "none",
       "auth_credentials": {},
       "custom_headers": null
     }'
   ```

3. Run simulations via UI or API

## Architecture

### Flow Diagram

```
AgentSim
   ↓ (HTTP POST /api/chat)
Cortex Wrapper Agent (FastAPI)
   ├─→ Pydantic AI Agent
   │   ├─→ Cortex LLM (Claude 4)
   │   │   └─→ Decides if database query needed
   │   └─→ @agent.tool: query_cortex_analyst
   │       ├─→ Cortex Analyst API
   │       │   └─→ Generates SQL from natural language
   │       └─→ Snowpark Session
   │           └─→ Executes SQL query
   └─→ Returns formatted response
```

### Key Components

1. **cortex_wrapper_agent.py** (~300 lines)
   - FastAPI server with `/api/chat` endpoint
   - Pydantic AI agent with system prompt
   - Cortex Analyst tool for database queries
   - Snowflake session management

2. **test_cortex_e2e.py** (~200 lines)
   - Automated E2E test script
   - Server lifecycle management
   - Test scenario execution

## Example Scenarios

The test includes realistic support data queries:
- "How many cases were opened last week?"
- "What are the top 3 product categories by ticket volume?"
- "Show me high priority escalated cases from the past month"

## Troubleshooting

### Cortex Agent Won't Start

**Error**: Connection refused or authentication error

**Solution**: Check your `.env` file has correct Snowflake credentials:
```bash
# Verify credentials
cat .env | grep SNOWFLAKE
```

### Session Expired Errors

**Error**: `390112: Session has expired`

**Solution**: The agent automatically retries with a fresh session. If it persists, check your Snowflake token expiry settings.

### Semantic Model Not Found

**Error**: Semantic model file not found

**Solution**: Update `SEMANTIC_MODEL_FILE` in `.env` to point to your semantic model:
```bash
SEMANTIC_MODEL_FILE=@YOUR_DATABASE.YOUR_SCHEMA.YOUR_STAGE/your_model.yaml
```

### Slow Responses

**Observation**: Simulations taking 5-10 seconds per turn

**Explanation**: This is normal! Cortex Analyst:
1. Generates SQL from natural language (~2s)
2. Executes query (~1-3s)
3. LLM formats results (~2s)

Consider increasing `timeout_seconds` in simulation config.

### Empty Results

**Error**: Cortex Analyst returns no SQL

**Solution**:
1. Check your semantic model is properly configured
2. Verify the question matches your data schema
3. Try simpler queries first

## Customization

### Using a Different Semantic Model

Edit `cortex_wrapper_agent.py`:

```python
semantic_model = os.getenv("SEMANTIC_MODEL_FILE", "@YOUR_STAGE/your_model.yaml")
```

### Changing the LLM Model

Edit `cortex_wrapper_agent.py`:

```python
model = SnowflakeCortexModel("claude-4-sonnet", provider=provider)  # or mistral-large, etc.
```

### Adjusting System Prompt

Edit the agent's system prompt in `cortex_wrapper_agent.py` to guide behavior:

```python
agent = Agent(
    model,
    system_prompt="Your custom instructions here...",
    ...
)
```

## Performance Tips

1. **Start with fewer simulations**: Use `num_simulations: 3` initially
2. **Use sequential execution**: Set `concurrency: 1` to avoid rate limits
3. **Increase timeouts**: Cortex queries can take 5-10 seconds
4. **Monitor costs**: Cortex Analyst queries consume credits

## Next Steps

Once testing is successful:
1. Increase simulation count for load testing
2. Test with edge cases and complex queries
3. Analyze metrics to identify improvement opportunities
4. Configure stop conditions based on your use case

## Support

For issues:
- Check AgentSim logs in console output
- Check Cortex agent logs in console output
- Review Snowflake query history for failed SQL
- Verify semantic model configuration

For questions about Cortex:
- See [Snowflake Cortex Documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex)
- Check Cortex Analyst semantic model guide
