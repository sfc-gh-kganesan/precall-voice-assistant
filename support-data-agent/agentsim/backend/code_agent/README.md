# Code Recommendation Agent

AI-powered code recommendation system that analyzes simulation insights and generates specific code improvements using Claude Agent SDK and GitHub MCP.

## Overview

This module extends AgentSim with automated code recommendation capabilities:
1. **LLM Judge** generates improvement insights from simulation failures
2. **Code Agent** reads insights and generates specific code changes with diffs
3. **GitHub MCP** provides tools to read code from the repository
4. Recommendations are saved directly to `ImprovementSuggestion` records

## Architecture

### Components

```
code_agent/
├── github_proxy.py      # FastMCP proxy for GitHub MCP (OAuth handling)
├── code_agent.py        # PydanticAI agent (insight → code recommendations)
└── README.md           # This file
```

### Data Flow

```
1. Simulation runs → Multiple conversations
2. LLM Judge analyzes → Creates ImprovementSuggestion records
3. Code Agent triggers → Reads insights from DB
4. For each insight:
   - Agent reads relevant code via GitHub MCP
   - Generates specific code changes with diffs
   - Saves to insight.code_recommendation (JSON column)
5. Frontend displays insights + code recommendations together
```

### Database Schema

Added single nullable JSON column to `ImprovementSuggestion`:

```python
code_recommendation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
```

Structure:
```json
{
  "file_changes": [
    {
      "file": "troubleshooting/app/agent.py",
      "old_content": "response = await client.post(url, json=data)",
      "new_content": "response = await client.post(url, json=data, timeout=30.0)",
      "diff": "- response = await client.post(url, json=data)\\n+ response = await client.post(url, json=data, timeout=30.0)"
    }
  ],
  "target_repo": "snowflakedb/aura",
  "target_path": "troubleshooting",
  "github_issue_url": null,
  "github_pr_url": null,
  "status": "pending",
  "generated_at": "2025-01-16T..."
}
```

## Usage

### 1. Setup GitHub Authentication

Get a GitHub Personal Access Token (PAT):

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (Full control of private repositories)
4. Generate and copy the token

Add to your `.env` file:
```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_your_actual_token_here
GITHUB_TOOLSETS=context,repos,issues,pull_requests
```

### 2. Start GitHub MCP Proxy

The proxy provides GitHub tools to the Code Agent:

```bash
cd agentsim
uv run backend/code_agent/github_proxy.py
```

- Uses PAT authentication (no browser flow)
- Runs on `http://localhost:8003/mcp`
- Exposes GitHub tools (read_file, search_code, etc.)

### 3. Generate Code Recommendations

#### For a single insight:
```python
from backend.code_agent.code_agent import generate_recommendation_for_insight

# Generate recommendation for insight ID 5
recommendation = await generate_recommendation_for_insight(
    insight_id=5,
    target_repo="snowflakedb/aura",
    target_path="troubleshooting"
)
```

#### For all insights in a simulation:
```python
from backend.code_agent.code_agent import generate_recommendations_for_simulation

# Generate for simulation ID 1
count = await generate_recommendations_for_simulation(
    simulation_id=1,
    target_repo="snowflakedb/aura",
    target_path="troubleshooting"
)
print(f"Generated {count} recommendations")
```

### 3. Test the Agent

```bash
cd agentsim
uv run backend/code_agent/code_agent.py 1  # simulation_id
```

## Environment Variables

Add to `agentsim/.env`:

```env
# Snowflake Cortex (for LLM backend)
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_PASSWORD=your-password

# GitHub Authentication
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_TOOLSETS=context,repos,issues,pull_requests

# Target repository
TARGET_REPO=snowflakedb/aura
TARGET_PATH=troubleshooting
```

## Dependencies

Added to `pyproject.toml`:
- `fastmcp>=0.1.0` - MCP proxy framework
- `claude-agent-sdk>=0.1.0` - Claude Agent SDK for agentic workflows
- `openai>=1.52.0` - Already present (for Cortex)

Install:
```bash
cd agentsim
uv sync
```

## Migration

Safe database migration (only adds nullable column):

```bash
cd agentsim
alembic revision --autogenerate -m "Add code_recommendation to ImprovementSuggestion"
alembic upgrade head
```

**Safety**: Nullable column means existing data is 100% safe.

## How It Works

### GitHub Proxy
- Connects to `https://api.githubcopilot.com/mcp/`
- Uses Personal Access Token (PAT) for authentication
- Exposes GitHub tools locally via FastMCP
- Tools available: `read_file`, `search_code`, `list_files`, etc.

### Code Agent
- Uses **Snowflake Cortex** as LLM (claude-4-sonnet)
- Connects to GitHub proxy for code access
- Custom tool: `get_simulation_insights()` reads from DB
- System prompt guides agent to generate diffs

### Workflow Per Insight
1. Agent loads `ImprovementSuggestion` from DB
2. Reads insight details (category, description, evidence)
3. Uses GitHub tools to read relevant code files
4. Analyzes the issue and generates fix
5. Creates diff in unified format
6. Saves to `insight.code_recommendation` JSON field

## API Integration (Future Phase 2)

Will add these endpoints to agentsim backend:

```python
# Generate recommendations
POST /api/simulations/{id}/code-recommendations
→ Triggers code agent for all insights

# Get recommendations
GET /api/simulations/{id}/insights
→ Returns insights with code_recommendation field populated

# Create GitHub issue
POST /api/insights/{id}/create-issue
→ Uses GitHub MCP to create issue with code diff

# Create GitHub PR
POST /api/insights/{id}/create-pr
→ Uses GitHub MCP to create pull request
```

## Benefits

✅ **Zero risk to data** - only adds nullable column
✅ **Simple schema** - no complex relationships
✅ **Natural mapping** - 1 insight → 1 code recommendation
✅ **Reuses patterns** - based on troubleshooting app's proven architecture
✅ **Modular** - can be tested/deployed independently
✅ **Flexible** - JSON structure easy to evolve

## Next Steps

### Phase 1 (Complete):
- [x] GitHub proxy with OAuth
- [x] Code agent with insights integration
- [x] Database schema extension
- [x] Basic testing capability

### Phase 2 (TODO):
- [ ] API routes for code recommendations
- [ ] Create GitHub issue functionality
- [ ] Create GitHub PR functionality (stretch)
- [ ] Auto-trigger after insights generation

### Phase 3 (TODO):
- [ ] Frontend UI to view recommendations
- [ ] View code diffs in UI
- [ ] Buttons to create issues/PRs
- [ ] Status tracking

## Troubleshooting

### "Connection refused" error
- GitHub proxy not running
- Start with: `uv run backend/code_agent/github_proxy.py`

### "GITHUB_TOKEN must be set" error
- PAT not configured in .env file
- Add `GITHUB_TOKEN=ghp_xxxxx` to agentsim/.env
- Get token from https://github.com/settings/tokens

### "Unauthorized" or "401" error
- GitHub PAT expired or invalid
- Generate new PAT with `repo` scope
- Update GITHUB_TOKEN in .env

### "No insights found"
- Simulation hasn't been analyzed by LLM judge yet
- Run insights generation first

### Agent generates no recommendations
- Check GitHub MCP connection
- Verify target_repo and target_path are correct
- Check agent logs for errors
