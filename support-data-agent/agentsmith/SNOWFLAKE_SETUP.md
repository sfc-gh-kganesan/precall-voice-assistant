# AgentSim Snowflake Integration

AgentSim supports both SQLite (for development) and Snowflake (for production) as database backends.

## Quick Start

### Using SQLite (Default)
No configuration needed! AgentSim will automatically use SQLite with a local `agentsim.db` file.

```bash
uvicorn backend.main:app --reload
```

### Using Snowflake

1. **Set up environment variables**:

```bash
cp .env.example .env
# Edit .env with your Snowflake credentials
```

2. **Configure `.env`**:

```bash
USE_SNOWFLAKE=true

SNOWFLAKE_ACCOUNT=your_account.region
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=AGENTSIM_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

3. **Install dependencies** (if not already installed):

```bash
uv sync
```

4. **Start the server**:

```bash
uvicorn backend.main:app --reload
```

The schema will be automatically created in Snowflake on first startup.

## Database Schema

AgentSim creates 7 tables in Snowflake:

1. **PROJECTS** - Agent project configurations  
2. **PERSONA_TEMPLATES** - Reusable test personas  
3. **SIMULATIONS** - Simulation runs  
4. **CONVERSATIONS** - Individual conversations  
5. **MESSAGES** - Conversation messages  
6. **CONVERSATION_METRICS** - Performance metrics  
7. **IMPROVEMENT_SUGGESTIONS** - AI-generated insights  

## Key Features

✅ **Dual-Mode Support** - SQLite for dev, Snowflake for prod  
✅ **VARIANT Types** - Native Snowflake semi-structured data  
✅ **Auto-Initialization** - Schema created automatically on startup  
✅ **Follows 360app Pattern** - Uses Snowpark for DDL  
✅ **SQLAlchemy Compatible** - Keep existing application code  

## Switching Backends

Simply change one environment variable:

- **Development**: `USE_SNOWFLAKE=false` (or omit)
- **Production**: `USE_SNOWFLAKE=true`

## Additional Documentation

See `LLM_JUDGES_IMPLEMENTATION.md` for details on the AI-powered insights feature.
