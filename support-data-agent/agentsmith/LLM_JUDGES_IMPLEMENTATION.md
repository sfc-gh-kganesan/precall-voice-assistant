# LLM Judges Implementation

This document describes the implementation of two LLM judges in AgentSim for intelligent stop conditions and AI-powered insights.

## Overview

Two Snowflake Cortex-powered LLM judges have been added to enhance AgentSim:

1. **Judge #1: Stop Condition Judge** - Evaluates conversations in real-time to determine intelligent stopping points
2. **Judge #2: Insights Judge** - Analyzes completed simulations to generate AI-powered improvement recommendations

## Judge #1: Stop Condition Judge

### Purpose
Intelligently determines when a conversation has reached completion by analyzing context, not just counting turns or time.

### Implementation Files
- `agentsim/backend/core/llm_judge.py` - Core LLM stop condition class

### Key Features
- Implements `StopCondition` interface
- Works **alongside** existing conditions (max_turns, timeout, agent_signal)
- Evaluates after each agent response
- Considers: goal achievement, conversation flow, user satisfaction signals
- Returns `StopReason.LLM_JUDGE` when conversation should stop
- Falls back gracefully if LLM call fails
- Configurable confidence threshold (default: 0.8)

### How It Works
1. After each agent response, the LLM judge analyzes the conversation history
2. Considers 5 criteria:
   - Goal Achievement: Has the user's issue been resolved?
   - Agent Completeness: Did the agent provide a complete response?
   - User Satisfaction Signals: Are there signs of satisfaction?
   - Conversation Flow: Is it wrapping up naturally?
   - Information Completeness: Has all info been exchanged?
3. Returns JSON with `should_stop`, `confidence`, and `reasoning`
4. Only stops if confidence >= threshold (default 0.8)

### Usage
Add LLMStopCondition to your simulation's stop conditions:

```python
from backend.core.llm_judge import LLMStopCondition

llm_condition = LLMStopCondition(
    api_key=os.getenv("SNOWFLAKE_CORTEX_API_KEY"),
    base_url=os.getenv("SNOWFLAKE_CORTEX_BASE_URL"),
    model="snowflake-arctic",
    confidence_threshold=0.8
)

# Add to simulator
stop_conditions.append(llm_condition)
```

## Judge #2: Insights Judge

### Purpose
Analyzes all conversations from a completed simulation to provide deep, AI-generated recommendations for agent improvement.

### Implementation Files
- `agentsim/backend/core/insights_judge.py` - Insights analysis engine
- `agentsim/backend/api/routes/insights.py` - API endpoints
- `agentsim/backend/models/models.py` - Database models (enhanced)
- `agentsim/backend/api/schemas.py` - API schemas
- `agentsim/frontend/src/app/simulations/[id]/insights/page.tsx` - UI

### Key Features
- Analyzes conversations in batch after simulation completes
- Generates 5-10 specific, actionable recommendations
- Stores results in `ImprovementSuggestion` table
- Categorizes by: tool, prompt, logic, error_handling, UX, performance
- Assigns priority: high, medium, low
- Includes evidence with conversation IDs and patterns
- Auto-generates after simulation completion
- Can regenerate on-demand

### How It Works
1. **Trigger**: After simulation completes, `simulation_runner.py` calls insights judge
2. **Data Collection**: Loads all conversations, messages, and metrics
3. **Analysis**: Sends comprehensive prompt to Snowflake Cortex with:
   - Simulation statistics (success rate, stop reasons)
   - Persona performance breakdown
   - Failed conversation examples
   - Successful conversation examples
4. **Parsing**: Extracts structured recommendations from LLM response
5. **Storage**: Saves to `ImprovementSuggestion` table with evidence
6. **Display**: Frontend shows both rule-based and AI insights

### API Endpoints

#### Get AI Insights
```
GET /api/simulations/{id}/ai-insights
```
Returns AI-generated insights. Generates on-demand if not yet created.

#### Regenerate Insights
```
POST /api/simulations/{id}/ai-insights/regenerate
```
Deletes existing insights and generates fresh ones.

### Frontend Integration
The insights page now shows two sections:
1. **Rule-Based Recommendations** - Original threshold-based logic
2. **AI-Powered Analysis** - LLM-generated insights with:
   - Category icons and badges
   - Priority indicators (high/medium/low)
   - Detailed evidence
   - Regenerate button

## Database Changes

### Simulation Model
Added fields:
- `llm_insights_generated` (bool): Track if insights have been generated
- `llm_insights_generated_at` (datetime): When insights were generated

### ImprovementSuggestion Model
Already existed, now actively used:
- `simulation_id`: Foreign key to simulation
- `category`: tool, prompt, logic, error_handling, ux, performance
- `title`: Short title
- `description`: Detailed explanation
- `priority`: high, medium, low
- `evidence`: JSON with conversation_ids, patterns, metrics

## Configuration

### Environment Variables
Required for LLM judges to work:

```bash
SNOWFLAKE_CORTEX_API_KEY=your_api_key
SNOWFLAKE_CORTEX_BASE_URL=your_base_url
SNOWFLAKE_CORTEX_MODEL=snowflake-arctic  # optional, defaults to snowflake-arctic
```

### Behavior Without Configuration
- **Stop Condition Judge**: Must be explicitly added to simulations (opt-in)
- **Insights Judge**: Skips generation with warning if Cortex not configured

## Files Created/Modified

### Backend - New Files
1. `agentsim/backend/core/llm_judge.py` - LLM Stop Condition Judge (206 lines)
2. `agentsim/backend/core/insights_judge.py` - Insights Analysis Judge (279 lines)
3. `agentsim/backend/api/routes/insights.py` - Insights API routes (132 lines)

### Backend - Modified Files
1. `agentsim/backend/core/interfaces.py` - Added `LLM_JUDGE` stop reason
2. `agentsim/backend/models/models.py` - Added insights tracking fields + relationship
3. `agentsim/backend/api/schemas.py` - Added insights response schemas
4. `agentsim/backend/services/simulation_runner.py` - Added insights generation trigger
5. `agentsim/backend/main.py` - Registered insights routes

### Frontend - Modified Files
1. `agentsim/frontend/src/lib/types.ts` - Added `ImprovementSuggestion` type
2. `agentsim/frontend/src/lib/api.ts` - Added AI insights endpoints
3. `agentsim/frontend/src/app/simulations/[id]/insights/page.tsx` - Enhanced UI

## Example Insights

### AI-Generated Insight Example
```json
{
  "category": "error_handling",
  "title": "Improve Timeout Error Recovery",
  "description": "15% of conversations failed due to timeouts when querying external services. The agent doesn't gracefully handle these cases and provides generic error messages instead of actionable guidance.",
  "priority": "high",
  "evidence": {
    "conversation_ids": [42, 51, 67, 88, 103],
    "affected_personas": ["Technical Expert", "Business Analyst"],
    "metrics": {"timeout_rate": 0.15, "avg_timeout_turn": 3},
    "pattern": "Timeouts occur most frequently when agent attempts to fetch large datasets without pagination"
  }
}
```

## Benefits

✅ **Intelligent Stop Detection**: Conversations end when truly complete, not arbitrarily
✅ **Deeper Insights**: AI finds patterns humans miss in large simulation batches
✅ **Actionable Recommendations**: Specific, prioritized suggestions with evidence
✅ **Complementary Approach**: Works alongside existing rule-based system
✅ **Uses Existing Infrastructure**: Leverages Snowflake Cortex already in use
✅ **Automatic Generation**: Insights generated automatically after simulations
✅ **On-Demand Regeneration**: Can refresh insights anytime via UI

## Next Steps (Optional Enhancements)

1. **Add LLM Stop Condition to Simulations**: Update simulation creation to optionally include LLM judge
2. **Insights Comparison**: Show diff between regenerated insights
3. **Trend Analysis**: Track insights across multiple simulation runs
4. **Conversation Links**: Make conversation IDs clickable in evidence
5. **Export Insights**: Allow downloading insights as PDF/CSV
6. **Custom Prompts**: Allow users to customize analysis prompts
7. **Multi-Model Support**: Add support for OpenAI, Anthropic in addition to Cortex

## Testing

### Test Stop Condition Judge
```python
# In your simulation configuration
from backend.core.llm_judge import LLMStopCondition
import os

llm_stop = LLMStopCondition(
    api_key=os.getenv("SNOWFLAKE_CORTEX_API_KEY"),
    base_url=os.getenv("SNOWFLAKE_CORTEX_BASE_URL"),
    model="snowflake-arctic",
    confidence_threshold=0.8
)
```

### Test Insights Judge
1. Run a simulation to completion
2. Navigate to insights page for that simulation
3. Wait for AI insights to load (may take 30-60 seconds)
4. Click "Regenerate" to test regeneration

### Manual API Testing
```bash
# Get AI insights
curl http://localhost:8000/api/simulations/1/ai-insights

# Regenerate insights
curl -X POST http://localhost:8000/api/simulations/1/ai-insights/regenerate
```

## Performance Considerations

- **LLM Stop Condition**: Adds ~500ms-2s per agent response (async, non-blocking)
- **Insights Generation**: Takes 30-90 seconds for 50 conversations
- **Cost**: Each stop evaluation costs ~$0.001, insights generation ~$0.05 per simulation
- **Caching**: Insights are cached in database, only regenerated on demand

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Simulation Flow                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │  Conversation Loop       │
            │  (simulator.py)          │
            └──────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │  Check Stop Conditions   │
            │  - Max Turns             │
            │  - Timeout               │
            │  - Agent Signal          │
            │  - LLM Judge ← NEW!      │
            └──────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │  Simulation Complete     │
            └──────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │  Insights Judge ← NEW!   │
            │  (simulation_runner.py)  │
            └──────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │  Store to Database       │
            │  (ImprovementSuggestion) │
            └──────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │  Display in Frontend     │
            │  (insights page)         │
            └──────────────────────────┘
```

## Contact & Support

For questions or issues with the LLM judges implementation, please open an issue on GitHub or contact the development team.
