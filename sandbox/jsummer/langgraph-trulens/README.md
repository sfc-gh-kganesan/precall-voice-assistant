# LangGraph with TruLens for Snowflake

A working recipe project demonstrating how to build and evaluate LangGraph workflows using TruLens, with deployment to Snowpark Container Services (SPCS). TruLens evaluation results are surfaced directly in Snowflake.

## Overview

This project provides a complete example of:

- **LangGraph Workflow** — A tool-calling agent with arithmetic operations
- **TruLens Integration** — Instrumented workflow with evaluation metrics captured in Snowflake
- **SPCS Deployment** — Containerized deployment to Snowpark Container Services
- **Observability** — Application logs, traces, and TruLens traces queryable from Snowflake Event Tables

## Project Structure

```
├── graph.py          # LangGraph workflow definition with tool nodes
├── evals.py          # TruLens evaluation harness and run configuration
├── metrics.py        # TruLens metric definitions (built-in and custom)
├── model.py          # Cortex LLM model wrapper
├── prompts.py        # System prompts
├── utils.py          # Snowpark session, logging, and tracing setup
├── LOGGING.md        # Recipes for querying logs and traces from Snowflake
├── release/          # SPCS deployment scripts and configuration
│   ├── deploy.sh
│   ├── snowflake.yml
│   └── service_spec.yaml
└── Dockerfile
```

## TruLens Evaluations

TruLens evaluations are computed and stored in Snowflake, accessible via the TruLens dashboard in Snowsight.

### Metrics

This project demonstrates both **out-of-the-box** and **custom** TruLens metrics:

| Metric | Type | Ground Truth |
|--------|------|--------------|
| `correctness` | Built-in (server-side) | ✓ Uses `GROUND_TRUTH_OUTPUT` |
| `Correctness with COT Reasons` | Built-in (client-side) | ✗ |
| `Custom Correctness Metric` | Custom | ✓ Uses `GROUND_TRUTH_OUTPUT` |

Ground truth values are passed via the `reference_output` parameter and captured as span attributes using `SpanAttributes.RECORD_ROOT.GROUND_TRUTH_OUTPUT`. These are then available for metrics that compare generated output against expected answers.

See `metrics.py` for metric implementations and `evals.py` for how ground truth is wired through the evaluation run.

## Logging and Tracing

See **[LOGGING.md](LOGGING.md)** for detailed recipes on extracting observability data from Snowflake Event Tables, including:

- Application logs from SPCS services
- Application traces (OpenTelemetry spans)
- Custom span attributes
- TruLens-specific traces via SDK

## Running Locally

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Snowflake account with Cortex access
- Environment variables for Snowflake connection (or `~/.snowflake/connections.toml`)

### Install Dependencies

```bash
uv sync
```

### Run the Evaluation

```bash
uv run python evals.py
```

This will:
1. Create a LangGraph workflow with tool-calling capabilities
2. Run evaluation queries through the workflow
3. Compute TruLens metrics (including ground truth comparisons)
4. Store results in Snowflake

## Deploying to SPCS

The `release/` directory contains everything needed to deploy the LangGraph workflow as an SPCS service.

### Prerequisites

- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) installed and configured
- Docker installed
- Appropriate Snowflake privileges for compute pools, image repositories, and services

### Configure

Before deploying, review and update the variables at the top of `release/deploy.sh` to match your target account and namespace:

```bash
COMPUTE_POOL=sandbox_compute_pool_cpu  # Your compute pool name
DATABASE=JSUMMER                        # Target database
SCHEMA=SANDBOX                          # Target schema
STAGE=DROPBOX                           # Stage for service spec
IMAGE_REPOSITORY=image_repository       # Image repository name
IMAGE=trulens                           # Docker image name
TAG=latest                              # Image tag
SERVICE_NAME=trulens                    # SPCS service name
```

### Deploy

```bash
cd release
./deploy.sh
```

The script will:
1. Create database and schema (if not exists)
2. Create compute pool and image repository
3. Build and push the Docker image
4. Deploy the SPCS service

## Service Function

For an example of exposing the LangGraph workflow as a **Service Function** (callable via SQL), see the sibling repository:

**[langgraph-service-function](../langgraph-service-function)**

