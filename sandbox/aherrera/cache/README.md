# Cortex Caching Experiments

Comprehensive framework for testing and comparing caching strategies for LLM-powered agents using Snowflake Cortex.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env with your Snowflake credentials (SNOWFLAKE_USER, SNOWFLAKE_PAT, etc.)

# 3. Setup caches and agents
source .venv/bin/activate
python setup_plan_cache.py
python setup_tool_cache.py
snowsql -f setup_cortex_agent.sql

# 4. Run comparison across all 5 experiments
python run_comparison.py
```

## Overview

This project implements and compares **5 different caching strategies** for LLM agents:

1. **Baseline** - No caching (performance baseline)
2. **Plan Cache** - Cache LLM planning decisions for similar workflows
3. **Tool Cache** - Cache individual tool execution results with semantic matching
4. **Full Cache** - Combine plan + tool caching for maximum coverage
5. **Cortex Agent** - Snowflake's managed agent service (for comparison)

All experiments use:
- **LangGraph** for agent orchestration
- **Snowflake Cortex LLM** (Claude 3.5 Sonnet) for reasoning
- **Cortex Search** for semantic similarity matching
- **TruLens** for observability and metrics

## Performance Results

Results from running 3 test queries (math operations) with realistic 7-second tool delays to simulate production workloads:

| Experiment      | Time (ms) | Plan Hits | Tool Hits | Total Hits | Speedup |
|-----------------|-----------|-----------|-----------|------------|---------|
| **baseline**        |    33,336 |         0 |         0 |          0 |   1.00x |
| **plan_cache**      |    26,518 |         3 |         0 |          3 |   1.26x |
| **tool_cache**      |    14,662 |         0 |         3 |          3 |   **2.27x** ⚡ |
| **full_cache**      |     9,749 |         3 |         3 |          6 |   **3.42x** 🚀 |
| **cortex_agent**    |    27,662 |       N/A |       N/A |          0 |   1.21x |

### Key Findings

- **Full cache is most effective** - Achieved 3.42x speedup by caching both LLM planning decisions AND tool execution results
- **Tool caching provides major value** - 2.27x speedup by caching slow tool execution (vs 1.01x with fast tools)
- **Plan cache alone has limited impact** - Only 1.26x speedup with slow tools, as tool execution dominates total time
- **Cortex Agent improved** - 1.21x speedup (still slower than custom caching but better than previous 0.39x)

**Recommendation**: Use **full cache** (plan + tool) for maximum performance with slow production tools. If simplicity is needed, **tool cache alone** still provides 2.27x speedup.

## Directory Structure

```
cache/
├── experiments/               # All 5 experiment implementations
│   ├── baseline/             # No caching (performance baseline)
│   ├── plan_cache/           # Cache LLM planning decisions
│   ├── semantic_tool/        # Cache tool execution results
│   ├── semantic_full/        # Cache both plans and tools
│   └── cortex_agent/         # Snowflake managed agent (REST API)
│
├── shared/                   # Shared utilities
│   ├── utils.py             # Snowpark session, logging, tracing
│   ├── cortex_models.py     # Cortex LLM wrappers
│   ├── cache_backends.py    # Cortex Search cache implementations
│   ├── trulens_config.py    # TruLens metrics and instrumentation
│   └── tools.py             # Math operation tools (add, multiply, etc.)
│
├── datasets/                # Test datasets
│   └── math_operations.json # 10 math queries with semantic variations
│
├── setup_plan_cache.py      # Create plan cache tables + search service
├── setup_tool_cache.py      # Create tool cache tables + search service
├── setup_cortex_agent.sql   # Create SPROCs for Cortex Agent
├── run_comparison.py        # Run all 5 experiments and compare results
└── README.md               # This file
```

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Snowflake account with Cortex access
- Snowflake role with permissions to:
  - Create tables, search services
  - Use Cortex functions (EMBED_TEXT_768, SEARCH_PREVIEW, COMPLETE)
  - Create and call stored procedures

### Installation

1. **Install dependencies:**
   ```bash
   uv sync
   source .venv/bin/activate
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your credentials:
   ```bash
   SNOWFLAKE_USER=your_username
   SNOWFLAKE_PAT=your_personal_access_token  # OAuth token for Cortex Agent
   SNOWFLAKE_ACCOUNT=your_account_locator
   SNOWFLAKE_DATABASE=AI_FDE
   SNOWFLAKE_SCHEMA=CACHE_EXPERIMENTS
   SNOWFLAKE_WAREHOUSE=your_warehouse
   SNOWFLAKE_ROLE=your_role
   ```

3. **Set up caches:**

   **Plan Cache** (for plan_cache + full_cache experiments):
   ```bash
   python setup_plan_cache.py
   ```
   Creates:
   - `AI_FDE.CACHE_EXPERIMENTS.plan_cache` table
   - `AI_FDE.CACHE_EXPERIMENTS.plan_cache_search` search service

   **Tool Cache** (for semantic_tool + full_cache experiments):
   ```bash
   python setup_tool_cache.py
   ```
   Creates:
   - `AI_FDE.CACHE_EXPERIMENTS.tool_cache` table
   - `AI_FDE.CACHE_EXPERIMENTS.tool_cache_search` search service

   **Cortex Agent** (for cortex_agent experiment):
   ```bash
   snowsql -f setup_cortex_agent.sql
   # Or via Python:
   python -c "from experiments.cortex_agent.create_agent import create_cortex_agent; create_cortex_agent()"
   ```
   Creates:
   - Math operation SPROCs: `add`, `multiply`, `divide`, `subtract`, `calculate_average`
   - Cortex Agent: `AI_FDE.CACHE_EXPERIMENTS.math_agent` (via REST API)

## Running Experiments

### Run All Experiments (Comparison)

The primary way to run experiments:

```bash
python run_comparison.py
```

This will:
1. Run **baseline** (no caching) - 3 queries
2. Run **plan_cache** with warmup (3 queries to populate cache) + test (3 cached queries)
3. Run **tool_cache** with warmup + test
4. Run **full_cache** with warmup + test
5. Run **cortex_agent** (REST API calls)
6. Display comparison table with speedups

### Run Individual Experiments

```bash
# Baseline
python -m experiments.baseline.run_baseline

# Plan cache
python -m experiments.plan_cache.run_plan_cache

# Tool cache
python -m experiments.semantic_tool.run_tool_cache

# Full cache (plan + tool)
python -m experiments.semantic_full.run_full_cache

# Cortex Agent
python -m experiments.cortex_agent.run_cortex_agent
```

## Experiments

### 1. Baseline

**No caching** - establishes performance baseline.

- Uses LangGraph with Cortex LLM (Claude 3.5 Sonnet)
- Agent plans tool usage, executes tools, returns final answer
- Every query goes through full LLM reasoning + tool execution
- **Files**: `experiments/baseline/graph_llm.py`, `run_baseline.py`

### 2. Plan Cache

**Caches LLM planning decisions** for semantically similar queries.

- **How it works**:
  1. Generate embedding for user query
  2. Search plan cache with 0.85 similarity threshold
  3. On hit: Skip LLM planning, execute cached tool calls directly
  4. On miss: Plan with LLM, execute tools, cache the plan

- **Best for**: Repeated workflow patterns, FAQs, similar phrasing
- **Performance**: **1.94x speedup** - best performer
- **Files**: `experiments/plan_cache/graph_llm.py`, `run_plan_cache.py`

### 3. Tool Cache (Semantic)

**Caches individual tool execution results** with semantic matching.

- **How it works**:
  1. Agent plans normally with LLM (no caching)
  2. For each tool call, search tool cache by tool name + input similarity
  3. On hit: Return cached output without executing tool
  4. On miss: Execute tool, cache result

- **Best for**: Dynamic queries with repeated operations (e.g., same calculations)
- **Performance**: **1.01x speedup** - minimal benefit (tools already fast)
- **Files**: `experiments/semantic_tool/graph_llm.py`, `run_tool_cache.py`

### 4. Full Cache (Plan + Tool)

**Combines plan caching AND tool caching** for maximum coverage.

- **How it works**:
  - **Layer 1**: Check plan cache (like #2)
  - **Layer 2**: Check tool cache for each tool call (like #3)
  - Caches both planning decisions and tool results

- **Best for**: Comprehensive caching strategy
- **Performance**: **1.29x speedup** - middle ground (overhead from dual caching)
- **Files**: `experiments/semantic_full/graph_llm.py`, `run_full_cache.py`

### 5. Cortex Agent

**Snowflake's managed agent service** via REST API (for comparison).

- **How it works**:
  1. Send query via REST API to `/api/v2/databases/.../agents/math_agent:run`
  2. Snowflake orchestrates planning, tool calls, reflection
  3. Returns streamed response via Server-Sent Events (SSE)

- **Authentication**: Uses OAuth token (`SNOWFLAKE_PAT`) with `Bearer` auth header
- **Tools**: Same math SPROCs as other experiments
- **Performance**: **0.39x speedup** (2.5x slower) - REST overhead + new thread per query
- **Files**: `experiments/cortex_agent/run_cortex_agent.py`, `create_agent.py`

## Architecture

### Cortex Integration

**LLM (Claude 3.5 Sonnet)**:
- Accessed via Snowflake Cortex `COMPLETE()` function
- Supports tool calling with structured JSON schemas
- Wrapped in LangChain-compatible interface

**Agent (Managed Service)**:
- REST API: `/api/v2/databases/{db}/schemas/{schema}/agents/{name}:run`
- OAuth authentication with Personal Access Token (PAT)
- Handles planning, tool execution, reflection automatically
- Streaming responses via SSE

**Search (Semantic Caching)**:
- `CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m', text)` for embeddings
- `CORTEX.SEARCH_PREVIEW()` for similarity search
- Configurable threshold (default: 0.85)

### Caching Architecture

**Plan Cache**:
```
User Query → Generate Embedding → Search Cache (threshold=0.85)
                                         ↓
                         ┌───────────────┴───────────────┐
                         │                               │
                    Cache HIT                       Cache MISS
                         │                               │
                         ↓                               ↓
              Execute Cached Tools              LLM Planning → Execute Tools
                         │                               │
                         └──────────────┬────────────────┘
                                        ↓
                                 Store in Cache
                                        ↓
                                  Final Answer
```

**Tool Cache**:
```
User Query → LLM Planning → For Each Tool Call:
                                    │
                                    ↓
              Tool Input → Generate Embedding → Search Cache (by tool_name + input)
                                                        ↓
                                     ┌──────────────────┴──────────────────┐
                                     │                                     │
                                Cache HIT                            Cache MISS
                                     │                                     │
                                     ↓                                     ↓
                           Return Cached Output                   Execute Tool
                                     │                                     │
                                     └────────────────┬────────────────────┘
                                                      ↓
                                               Store in Cache
                                                      ↓
                                               Tool Results → LLM → Final Answer
```

### Observability

**TruLens Integration**:
- `TruGraph` wrapper for LangGraph workflows
- Tracks cache hits, latency, cost savings
- Metrics stored in Snowflake for analysis
- OpenTelemetry tracing for distributed debugging

**Metrics Collected**:
- Cache hit rate (plan, tool, overall)
- Latency (P50/P95/P99, cached vs uncached)
- Token usage and cost savings
- Correctness vs ground truth

## Development Status

### ✅ Completed

- All 5 experiments implemented and working
- Comparison framework (`run_comparison.py`)
- Setup scripts for all cache types
- Performance baselines established
- Cortex Agent REST API integration
- TruLens observability
- Math operations dataset

### 📋 Future Work

- Thread reuse optimization for Cortex Agent (avoid cold starts)
- Additional datasets (SQL queries, multi-step reasoning)
- Cost analysis (token usage savings)
- Cache TTL and eviction strategies
- Experiment config file (YAML)
- Results visualization dashboard

## Datasets

### math_operations.json

10 arithmetic test cases with semantic variations:
- Simple operations: add, multiply, divide, subtract
- Complex operations: average calculation
- Multi-step: compound operations

Each test case includes:
- `query`: Natural language math question
- `reference_output`: Expected answer
- `similar_queries`: Semantic variations for cache testing
- `tools_needed`: Which tools should be called

**Example**:
```json
{
  "id": "math_001",
  "query": "What is 15 multiplied by 4?",
  "reference_output": "60",
  "similar_queries": [
    "Calculate 15 times 4",
    "15 * 4 = ?",
    "Multiply fifteen by four"
  ],
  "tools_needed": ["multiply"]
}
```

## References

- [Snowflake Cortex LLM](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)
- [Cortex Search](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [TruLens](https://www.trulens.org/)
- [Snowflake REST API Authentication](https://docs.snowflake.com/en/developer-guide/sql-api/authenticating)
