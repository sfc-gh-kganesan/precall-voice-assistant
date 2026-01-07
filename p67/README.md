# Project 67

Experimental platform for building, testing, and deploying agentic workflows on Snowflake.

## Project Structure

```
.
├── packages/
│   ├── agent-sdk/    # Agent SDK for P67 workflows
│   ├── db/           # Database client with Prisma integration
│   └── web/          # React 19 + Vite frontend
├── services/
│   └── controld/     # Control plane service (Fastify-based)
├── tools/
│   └── p67-cli/      # P67 CLI tool for workflow management
├── coco/             # Cortex Code custom commands and demos
├── example_workflows/
│   ├── number_one/   # Example LangGraph workflow
│   └── template/     # Workflow template
├── native-app/       # Snowflake Native Application
├── ops/              # Operational SQL scripts (Postgres setup/teardown)
├── scripts/          # Utility scripts
├── Dockerfile        # Multi-service Docker build
├── compose.yaml      # Docker Compose orchestration
└── pnpm-workspace.yaml
```

## Tech Stack

**Packages:**
- **agent-sdk:** TypeScript SDK for building P67 workflows with Snowflake integration
- **db:** Prisma + PostgreSQL adapter for database operations
- **web:** React 19, TypeScript, Vite, Mantine UI

**Services:**
- **controld:** Fastify 5.2.0, Zod validation, OpenAPI/Swagger, workflow runtime

**Tools:**
- **p67-cli:** Bun-based CLI for workflow lifecycle management
- **Biome:** Code linting and formatting
- **pnpm:** Package management (v10.22.0)

## Getting Started

### Prerequisites

- Node.js v20 or higher
- pnpm v10.22.0
- Bun runtime (for p67-cli)
- Docker & Docker Compose (for local services)

### Installation

Install dependencies across all packages:

```bash
pnpm install
```

### Development

Run all services in development mode:

```bash
pnpm dev
```

This starts:
- **Web:** http://localhost:5173
- **Controld:** http://localhost:3002

Or run services individually:

```bash
# Control plane service
cd services/controld && pnpm dev

# Web frontend
cd packages/web && pnpm dev
```

### Building

Build all packages:

```bash
pnpm build
```

Or build specific packages:

```bash
cd packages/agent-sdk && pnpm build
cd packages/db && pnpm build
cd packages/web && pnpm build
```

### Code Quality

```bash
# Lint and format check
pnpm check

# Auto-fix issues
pnpm fix

# Type checking
pnpm type:check

# Run all CI checks
pnpm ci
```

## CLI Tool (p67-cli)

The `p67` CLI manages workflow lifecycle, connections, and project initialization.

### Installation

```bash
cd tools/p67-cli
make clean install
```

### Usage

```bash
# Initialize new project
p67 init my-workflow

# Manage connections
p67 connection add
p67 connection list
p67 connection set-default <name>

# Build workflow
p67 build

# Deploy workflow
p67 workflow deploy <zip-file>

# Run workflow
p67 workflow run [workflow-id]

# List workflows
p67 workflow list
```

See [tools/p67-cli/README.md](tools/p67-cli/README.md) for detailed CLI documentation.

## Services

### Controld - Control Plane Service

Located in `services/controld/`, provides workflow execution and management APIs.

**Features:**
- Workflow deployment via ZIP upload
- Workflow execution runtime using Bun
- LangGraph workflow support
- File-based storage
- OpenAPI documentation at `/docs`

**API Endpoints:**
- `GET /api/health` - Health check
- `POST /api/workflow/create` - Upload workflow
- `GET /api/workflow/list` - List workflows
- `POST /api/workflow/:workflowId/run` - Execute workflow
- `GET /docs` - Swagger UI
- `GET /docs/json` - OpenAPI schema

**Local Development:**
```bash
cd services/controld
pnpm dev  # Runs on http://localhost:3002
```

## Packages

### agent-sdk

TypeScript SDK for building workflows with Snowflake Cortex features:
- Execute read-only SQL queries
- Query Cortex Analyst with natural language
- Call Cortex Agent with streaming support

### db

Database utilities with Prisma client and PostgreSQL adapter:
- Fastify plugin integration
- Connection management
- Type-safe database operations

### web

React frontend application with Mantine UI components (currently experimental).

## Docker Deployment

### Local Development with Docker Compose

```bash
# Start all services
docker compose up

# Rebuild and start
docker compose up --build

# Stop services
docker compose down
```

Services:
- **Postgres:** localhost:5432
- **Controld:** http://localhost:3002

### Build Docker Image

```bash
# Build controld service
docker build --build-arg SERVICE_NAME=controld -t p67-controld .

# Run controld
docker run -p 3002:3000 p67-controld
```

## CoCo (Cortex Code) Integration

The `coco/` directory contains custom commands and demos for Snowflake Cortex Code:

```bash
cd coco
make  # Initialize and launch CoCo environment
```

Includes:
- Custom commands for P67 workflows
- Demo projects showcasing workflow patterns
- Skills for Cortex Code

## Example Workflows

### number_one

LangGraph-based workflow demonstrating:
- Multi-node state management
- Sequential workflow execution
- Graph compilation and execution

### template

Starter template for new workflow projects.

## Database Operations

### Postgres Setup

```bash
# Set up Postgres service in Snowflake
snowsql -f ops/postgres_setup.sql

# Tear down Postgres service
snowsql -f ops/postgres_teardown.sql
```

### Database Migrations

```bash
cd packages/db

# Run migrations locally
make deploy

# View pending migrations
make diff

# Generate Prisma client
pnpm db:generate
```

## CI/CD

GitHub Actions workflows:
- **p67-ci.yml:** Runs linting, type checking, and builds on PR
- **p67-migrate-db.yml:** Database migration deployment (manual trigger)

## Configuration Files

- **biome.json:** Biome linter/formatter config (4-space indentation)
- **tsconfig.json:** Root TypeScript configuration
- **pnpm-workspace.yaml:** pnpm workspace definition
- **.editorconfig:** Editor configuration
- **Makefile:** Common development tasks

## Project Configuration

Each workflow project uses `p67.yml` for configuration:

```yaml
entrypoint: ./src/index.ts
buildDir: .bundle
```

Connection configuration stored in `~/.snowflake/p67/config.toml`:

```toml
default_connection_name = "dev"

[connections.dev]
endpoint = "https://your-endpoint.snowflakecomputing.app"
pat = "your_pat_token"
```

## License

ISC
