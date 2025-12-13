# Project 67

Experimental platform for building, testing, and deploying agentic workflows.

## Project Structure

```
.
├── packages/
│   ├── api/          # Fastify backend API
│   └── web/          # React 19 + Vite frontend
├── services/
│   ├── harness/      # Workflow harness service (Hono-based)
│   └── controld/     # Control plane service (Fastify-based)
├── tools/
│   └── p67-cli/      # P67 CLI tool
├── native-app/       # Snowflake Native Application
├── scripts/          # Operational scripts
├── package.json
└── pnpm-workspace.yaml
```

## Tech Stack

- **Backend (packages/api):**
  - TypeScript
  - Fastify
  - Node.js

- **Control Plane (services/controld):**
  - TypeScript
  - Fastify 5.2.0
  - Zod validation with fastify-type-provider-zod
  - OpenAPI/Swagger UI
  - Node.js

- **Harness (services/harness):**
  - TypeScript
  - Hono 4.10.8
  - Zod validation with @hono/zod-openapi
  - OpenAPI/Swagger UI
  - Node.js

- **Frontend (packages/web):**
  - React 19
  - TypeScript
  - Vite
  - Mantine UI (Component Library)
  - ESLint

## Getting Started

### Prerequisites

- Node.js (v18 or higher recommended)
- pnpm v10.22.0 or higher

### Installation

Setup artifactory auth (needed for accessing internal Snowflake node modules):

```bash
sf artifact npm setup-auth -r internal-production-npm-snowflake-virtual
```

Install all dependencies:

```bash
pnpm install
```

### Development

Run both frontend and backend in parallel:

```bash
pnpm dev
```

Or run them individually:

```bash
# Backend only (runs on port 3001)
pnpm dev:api

# Frontend only (runs on port 5173)
pnpm dev:web

# Harness service (runs on port 8000)
cd services/harness && pnpm dev

# Controld service (runs on port 3002)
cd services/controld && pnpm dev
```

### Building

Build all packages:

```bash
pnpm build
```

Or build individually:

```bash
pnpm build:api
pnpm build:web
```

### Type Checking

Run type checking across all packages:

```bash
pnpm type-check
```

## API Endpoints

### API Service (port 3001)

The backend API runs on `http://localhost:3001` and includes:

- `GET /api/health` - Health check endpoint
- `GET /api/hello` - Sample API endpoint

### Controld Service (port 3002)

The control plane service runs on `http://localhost:3002` and includes:

- `GET /api/health` - Health check endpoint
- `GET /docs` - Swagger UI documentation
- `GET /docs/json` - OpenAPI schema

### Harness Service (port 8000)

The workflow harness service runs on `http://localhost:8000` and includes:

- `GET /api/health` - Health check endpoint
- `POST /api/workflows` - Create workflow
- `GET /api/workflows` - List workflows
- `POST /api/workflows/:workflowId/run` - Run workflow
- `GET /docs` - Swagger UI documentation
- `GET /openapi.json` - OpenAPI schema

## Frontend

The frontend runs on `http://localhost:5173` during development.

## Services

### Controld - Control Plane Service

Located in `services/controld/`, the control plane service is built with Fastify and provides API functionality for managing P67 platform operations.

**Features:**
- Fastify 5.2.0 framework
- Type-safe validation with Zod
- Automatic OpenAPI schema generation
- Swagger UI at `/docs`
- Built-in logging with Pino

**Documentation:** See [services/controld/README.md](services/controld/README.md)

### Harness - Workflow Execution Service

Located in `services/harness/`, the harness service executes and manages agentic workflows.

**Features:**
- Hono 4.10.8 framework
- Workflow deployment via ZIP upload
- Workflow execution runtime
- OpenAPI/Swagger documentation
- File-based storage

**Documentation:** See [services/harness/README.md](services/harness/README.md) (if exists)
