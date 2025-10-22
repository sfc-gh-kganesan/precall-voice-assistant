# LangGraph Service Function

A reference implementation for deploying LangGraph workflows as Snowflake service functions using Snowpark Container Services (SPCS).

## Overview

This project demonstrates the **service function pattern** in SPCS, where a containerized LangGraph workflow is deployed as a Snowflake service and exposed as a SQL-callable function. This pattern enables:

- **Scalable AI workflows**: Run complex LangGraph agents within Snowflake's compute infrastructure
- **SQL integration**: Invoke LangGraph workflows directly from SQL queries
- **Unified data platform**: Keep AI logic close to your data without external dependencies
- **Automatic scaling**: SPCS handles container orchestration, scaling, and lifecycle management

## What This Example Does

The example implements a simple LangGraph workflow that:
1. Takes a name as input
2. Generates a random age (via `first_node`)
3. Returns a personalized birthday greeting (via `second_node`)

The workflow is deployed as `LANGGRAPH_FUNCTION` and can be called like any Snowflake function:

```sql
SELECT LANGGRAPH_FUNCTION('Alice');
-- Returns: {"result": "Hello, Alice! I can't believe it's your 42 birthday."}
```

## Project Structure

```
langgraph-service-function/
├── app.py                    # FastAPI application entry point
├── graph.py                  # LangGraph workflow definition
├── utils.py                  # SPCS helper utilities
├── Dockerfile                # Container image definition
├── pyproject.toml            # Python dependencies (uv)
└── release/
    ├── snowflake.yml         # Snowflake project configuration
    ├── service_spec.yaml     # SPCS service specification
    ├── function.sql          # Service function DDL
    └── deploy.sh             # Deployment script
```

## Prerequisites

- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli-v2/index) (v3.12.0+)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Snowflake account with SPCS enabled
- Appropriate Snowflake privileges (see below)

**Required Snowflake Privileges:**
- `CREATE DATABASE`, `CREATE SCHEMA`
- `CREATE COMPUTE POOL`
- `CREATE IMAGE REPOSITORY`, `CREATE SERVICE`
- `CREATE FUNCTION`

## Configuration

The deployment is configured in `release/snowflake.yml`:

```yaml
definition_version: 2
entities:
  compute_pool:
    type: compute-pool
    identifier: <% ctx.env.COMPUTE_POOL %>
    min_nodes: 1
    max_nodes: 1
    instance_family: CPU_X64_XS
    auto_resume: true
    initially_suspended: true
    auto_suspend_seconds: 60
  image_repository:
    type: image-repository
    identifier:
      name: <% ctx.env.IMAGE_REPOSITORY %>
      database: <% ctx.env.DATABASE %>
      schema: <% ctx.env.SCHEMA %>
  langgraph:
    type: service
    identifier: 
      name: langgraph
      database: <% ctx.env.DATABASE %>
      schema: <% ctx.env.SCHEMA %>
    stage: <% ctx.env.STAGE %>
    compute_pool: <% ctx.env.COMPUTE_POOL %>
    spec_file: service_spec.yaml
    min_instances: 1
    max_instances: 1
    auto_resume: true
    artifacts:
      - service_spec.yaml
    comment: "LangGraph service"
```

## Deployment

### Quick Start

1) Edit the values at the top of `/release/deploy.sh` as you desire. We assume everything is contained in a single database + schema.
```bash
COMPUTE_POOL=sandbox_compute_pool_cpu
DATABASE=JSUMMER
SCHEMA=SANDBOX
STAGE=DROPBOX
IMAGE_REPOSITORY=image_repository
IMAGE=langgraph-service-function
TAG=latest
SERVICE_NAME=langgraph
```

2) Run the script:
```bash
cd release
export SNOW_CONNECT="--connection default" # Optional
./deploy.sh
```

### What the Script Does

The `deploy.sh` script automates the complete deployment:

1. **Creates infrastructure**: Database, schema, compute pool, image repository
2. **Authenticates**: Logs into Snowflake container registry
3. **Builds container**: Creates multi-platform Docker image (linux/amd64)
4. **Pushes image**: Uploads to Snowflake image repository
5. **Updates spec**: Sets the image URL in service spec
5. **Deploys service**: Creates SPCS service from `service_spec.yaml`
6. **Creates function**: Deploys `LANGGRAPH_FUNCTION` SQL wrapper

### Connection Configuration

Use the `SNOW_CONNECT` environment variable to pass additional Snowflake CLI flags:

```bash
# Use a specific connection from ~/.snowflake/config.toml
export SNOW_CONNECT="--connection prod"

# Specify connection parameters directly
export SNOW_CONNECT="--account myaccount --user myuser --warehouse compute_wh"

# Use with role and warehouse overrides
export SNOW_CONNECT="--connection default --role DEVELOPER --warehouse DEV_WH"

./deploy.sh
```

**Tip:** Any valid Snowflake CLI connection flag can be passed via `SNOW_CONNECT`.

## Testing

Once deployed, test the function in Snowflake:

```sql
-- Simple invocation
SELECT LANGGRAPH_FUNCTION('Alice');

-- Use in a query
SELECT 
    name,
    LANGGRAPH_FUNCTION(name) as greeting
FROM users;
```

Check service status:

```bash
snow spcs service status langgraph --database JSUMMER --schema SANDBOX
snow spcs service logs langgraph --container-name langgraph-service-function
```

## Customization

To adapt this pattern for your own LangGraph workflow:

1. **Update the workflow**: Modify `graph.py` with your LangGraph logic
2. **Adjust dependencies**: Add required packages to `pyproject.toml`
3. **Update schema**: Change the function signature in `release/function.sql`
4. **Configure resources**: Adjust identifiers in `snowflake.yml`

## Architecture

```
┌────────────────────────────────────────────────┐
│  Snowflake                                     │
│  ┌─────────────────────────────────────────┐   │
│  │  SQL Query                              │   │
│  │  SELECT LANGGRAPH_FUNCTION('Alice')     │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                           │
│  ┌─────────────────▼───────────────────────┐   │
│  │  Service Function (SQL Wrapper)         │   │
│  │  Maps SQL types to HTTP requests        │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                           │
│  ┌─────────────────▼───────────────────────┐   │
│  │  SPCS Service (Container)               │   │
│  │  ┌─────────────────────────────────┐    │   │
│  │  │ FastAPI (app.py)                │    │   │
│  │  │   ↓                             │    │   │
│  │  │ LangGraph Workflow (graph.py)   │    │   │
│  │  └─────────────────────────────────┘    │   │
│  └─────────────────────────────────────────┘   │
└────────────────────────────────────────────────┘
```

## Resources

- [Snowflake Service Functions](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/service-function)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Snowflake CLI Reference](https://docs.snowflake.com/en/developer-guide/snowflake-cli-v2/index)

