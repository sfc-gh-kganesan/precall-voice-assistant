# P67 Project - Claude Code Instructions

This document provides guidance for Claude Code when working with the P67 monorepo project.

## Project Overview

P67 (Project 67, also known as "Cortex Mesh") is an experimental platform for building, testing, and deploying agentic workflows on Snowflake. It's a modern full-stack TypeScript monorepo that combines traditional web applications with workflow orchestration capabilities.

The repository contains:
- **packages/**: Traditional web application packages (API and frontend)
- **services/**: Backend microservices (Harness workflow service)
- **tools/**: Command-line interface tools (p67 CLI)
- **native-app/**: Snowflake Native Application configuration
- **scripts/**: Shell scripts for workflow operations
- **example_workflows/**: Sample workflow projects
- **coco/**: Claude Code custom environment setup

## Architecture

P67 enables users to:
1. Build agentic workflows using LangGraph or other frameworks
2. Package workflows as ZIP files
3. Deploy workflows to the Harness service (local or Snowflake SPCS)
4. Execute workflows and retrieve results
5. Manage workflows via CLI or API

## Technology Stack Summary

### Frontend Stack
- **Framework**: React 19.2.0
- **Build Tool**: Vite 7.2.2
- **UI Library**: Mantine UI v8
- **Language**: TypeScript 5.9.3

### Backend Stack
- **API Service**: Fastify 5.2.0
- **Harness Service**: Hono 4.10.8
- **Runtime**: Node.js with ESM modules
- **Language**: TypeScript 5.9.3

### CLI Stack
- **Runtime**: Bun (fast JavaScript runtime)
- **CLI Framework**: Commander.js 12.1.0
- **Prompts**: @inquirer/prompts 8.0.2
- **Validation**: Zod 4.1.13

### Infrastructure
- **Container Platform**: Docker
- **Deployment Target**: Snowflake SPCS (Snowpark Container Services)
- **Package Manager**: pnpm 10.22.0
- **Native Apps**: Snowflake Native Application framework

### Development Tools
- **Linting**: ESLint 9 with TypeScript support
- **Formatting**: Prettier 3.3.0
- **Type Checking**: TypeScript strict mode
- **Testing**: Vitest 4.0.9 (web package)
- **Version Control**: Git

## Project Structure

```
p67/
├── packages/                       # Traditional web applications
│   ├── api/                        # Fastify backend API service
│   │   ├── src/
│   │   │   └── index.ts            # Main Fastify server
│   │   ├── dist/                   # Compiled output
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── web/                        # React frontend application
│       ├── src/
│       │   ├── main.tsx            # React entry point
│       │   ├── App.tsx             # Main component
│       │   ├── App.css
│       │   └── index.css
│       ├── public/                 # Static assets
│       ├── index.html
│       ├── vite.config.ts
│       ├── package.json
│       └── tsconfig*.json
│
├── services/                       # Backend microservices
│   └── harness/                    # Workflow harness service
│       ├── src/
│       │   ├── index.ts            # Main Hono server
│       │   ├── config.ts           # Configuration
│       │   ├── schema.ts           # Zod schemas
│       │   ├── runner.ts           # Workflow execution
│       │   ├── routes/             # API routes
│       │   │   ├── api.ts          # Main API router
│       │   │   ├── health.ts       # Health check
│       │   │   └── workflow.ts     # Workflow operations
│       │   ├── middleware/         # Middleware
│       │   │   ├── error-handler.ts
│       │   │   ├── logger.ts
│       │   │   └── env.ts
│       │   └── lib/                # Utilities
│       │       ├── file-storage.ts # File system ops
│       │       ├── zip.ts          # ZIP handling
│       │       └── env.ts          # Env helpers
│       ├── Dockerfile              # Service Docker image
│       ├── harness_spec.yaml       # SPCS service spec
│       ├── package.json
│       └── tsconfig.json
│
├── tools/                          # Command-line tools
│   └── p67-cli/                    # P67 CLI application
│       ├── src/
│       │   ├── index.ts            # CLI entry point
│       │   ├── commands/           # Command modules
│       │   │   ├── init.ts         # Initialize config
│       │   │   ├── env.ts          # Environment/secrets
│       │   │   └── workflow/       # Workflow commands
│       │   │       ├── index.ts    # Main workflow cmd
│       │   │       ├── deploy.ts   # Deploy workflow
│       │   │       ├── list.ts     # List workflows
│       │   │       └── run.ts      # Execute workflow
│       │   ├── config/
│       │   │   └── ProjectConfig.ts # Config management
│       │   ├── clients/
│       │   │   └── HarnessClient.ts # HTTP client
│       │   └── secrets/
│       │       └── 1password.ts    # 1Password integration
│       ├── bin/                    # Compiled binary
│       ├── CLAUDE.md               # CLI documentation
│       ├── package.json
│       └── tsconfig.json
│
├── native-app/                     # Snowflake Native App
│   ├── manifest.yml                # App manifest
│   ├── setup.sql                   # Setup procedures
│   └── README.md
│
├── scripts/                        # Operational scripts
│   ├── local_create_workflow.sh    # Create workflow locally
│   ├── local_list_workflows.sh     # List local workflows
│   ├── local_run_workflow.sh       # Run workflow locally
│   ├── spcs_create_workflow.sh     # Create workflow on SPCS
│   ├── spcs_list_workflows.sh      # List SPCS workflows
│   ├── spcs_run_workflow.sh        # Run workflow on SPCS
│   ├── spcs_healthcheck.sh         # SPCS health check
│   └── get_spcs_endpoint_harness.sh # Get SPCS endpoint
│
├── coco/                           # Claude Code environment
│   ├── commands/                   # Custom slash commands
│   │   ├── define-workflow.md
│   │   └── generate-workflow.md
│   ├── skills/                     # Custom skills
│   ├── demo/                       # Demo templates
│   └── setup.sh                    # Setup script
│
├── example_workflows/              # Example workflows
│   └── number_one/                 # LangGraph example
│       ├── src/
│       ├── package.json
│       ├── p67.yml                 # P67 configuration
│       └── build.js                # esbuild script
│
├── experiments/                    # Experimental projects
│   └── flask-ui/                   # Flask UI experiment
│       ├── app.py
│       └── requirements.txt
│
├── ops/                            # Operational SQL scripts
│
├── Dockerfile                      # Multi-stage Docker build
├── compose.yaml                    # Docker Compose config
├── Makefile                        # Build and deployment commands
├── snowflake.yml                   # Snowflake CLI config
├── .prettierrc                     # Prettier configuration
├── .prettierignore                 # Prettier ignore patterns
├── package.json                    # Root workspace config
├── pnpm-workspace.yaml             # Workspace definition
└── pnpm-lock.yaml                  # Dependency lock file
```

## Component Details

### 1. Packages (@p67/api and @p67/web)

#### @p67/api - Backend API Service

**Purpose**: General-purpose Fastify-based backend API service

**Technology Stack**:
- **Runtime**: Node.js with ESM modules
- **Framework**: Fastify 5.2.0 (fast, low-overhead web framework)
- **Language**: TypeScript 5.9.3 targeting ES2022
- **Dev Tools**: tsx for development with watch mode
- **CORS**: @fastify/cors for cross-origin requests
- **Server**: Runs on port 3001 (configurable via PORT env var)

**Current Endpoints**:
- `GET /api/health` - Health check endpoint
  - Returns: `{ status: 'ok', timestamp: ISO8601 }`
- `GET /api/hello` - Sample greeting endpoint
  - Returns: `{ message: 'Hello from Fastify!' }`

**Scripts**:
- `pnpm dev` - Start dev server with hot reload (tsx watch)
- `pnpm build` - Compile TypeScript to JavaScript
- `pnpm start` - Run production build
- `pnpm lint` / `pnpm lint:fix` - ESLint
- `pnpm format` / `pnpm format:check` - Prettier
- `pnpm type:check` - TypeScript validation

#### @p67/web - Frontend Application

**Purpose**: React-based frontend web application

**Technology Stack**:
- **Framework**: React 19.2.0 (latest version)
- **Build Tool**: Vite 7.2.2 (next-generation frontend tooling)
- **Language**: TypeScript 5.9.3
- **UI Library**: Mantine UI v8 (component library)
- **Styling**: PostCSS with postcss-preset-mantine
- **Dev Server**: Runs on port 5173
- **Plugins**: @vitejs/plugin-react for Fast Refresh and JSX
- **Testing**: Vitest 4.0.9

**Scripts**:
- `pnpm dev` - Start Vite dev server
- `pnpm build` - Build for production
- `pnpm preview` - Preview production build
- `pnpm lint` / `pnpm lint:fix` - ESLint
- `pnpm format` / `pnpm format:check` - Prettier
- `pnpm type:check` - TypeScript validation

### 2. Services (@p67/harness)

#### @p67/harness - Workflow Harness Service

**Purpose**: Executes and manages agentic workflows. This is the core service that runs workflows deployed by users.

**Technology Stack**:
- **Runtime**: Node.js with ESM modules
- **Framework**: Hono 4.10.8 (lightweight, fast web framework)
- **Server**: @hono/node-server
- **API Documentation**: @hono/swagger-ui, @hono/zod-openapi
- **Validation**: Zod 4.1.13 for schema validation
- **Logging**: Pino 10.1.0 with hono-pino
- **File Handling**: adm-zip for ZIP operations
- **Language**: TypeScript 5.9.3
- **Target**: ES2022
- **Port**: 8000 (configurable via PORT env var)

**Architecture**:
- OpenAPI 3.1.0 compliant REST API
- Swagger UI documentation at `/docs`
- File-based workflow storage (configurable via `DATA_ROOT`)
- ZIP file upload/extraction for workflow deployment
- Workflow execution runtime

**API Endpoints**:
- `GET /api/health` - Health check endpoint
- `POST /api/workflows` - Create workflow (accepts ZIP file upload)
- `GET /api/workflows` - List all workflows
- `POST /api/workflows/:workflowId/run` - Execute a workflow

**Storage**:
- Local file system storage (default: `.local-storage/`)
- Configurable via `DATA_ROOT` environment variable
- Workflows stored as extracted ZIP contents

**Deployment**:
- Docker containerized (multi-stage Dockerfile)
- Snowflake SPCS (Snowpark Container Services) ready
- Local development via Docker Compose
- Service specification in `harness_spec.yaml`

**Scripts**:
- `pnpm dev` - Development server with tsx watch
- `pnpm build` - Compile TypeScript
- `pnpm start` - Production server
- `pnpm lint` / `pnpm lint:fix` - ESLint
- `pnpm format` / `pnpm format:check` - Prettier
- `pnpm type:check` - TypeScript validation

### 3. Tools (@p67/cli)

#### @p67/cli - P67 Command-Line Interface

**Purpose**: Command-line tool for managing P67 workflows, providing an easy interface for deploying, listing, and running workflows.

**Technology Stack**:
- **Runtime**: Bun (fast JavaScript runtime)
- **CLI Framework**: Commander.js 12.1.0
- **Interactive Prompts**: @inquirer/prompts 8.0.2
- **Validation**: Zod 4.1.13
- **Config Format**: YAML (js-yaml 4.1.1)
- **Secrets Management**: 1Password integration (@1password/op-js)
- **Language**: TypeScript 5+
- **Module System**: ESNext with bundler resolution

**Configuration (p67.yml)**:
```yaml
runtime:
  endpoint: <harness-service-url>
```

**Commands**:
- `p67 init` - Initialize p67.yml configuration file
- `p67 env` - Show environment configuration and secrets
- `p67 workflow deploy` - Deploy a workflow ZIP to the harness
- `p67 workflow list` - List all deployed workflows
- `p67 workflow run <workflowId>` - Execute a workflow

**Features**:
- Interactive prompts for user-friendly experience
- Zod schema validation for type safety
- TypeScript-first design
- Personal Access Token (PAT) authentication
- 1Password integration for secrets management
- Fast execution with Bun runtime

**Scripts**:
- `pnpm start` - Run CLI with Bun
- `pnpm build` - Compile to binary
- `pnpm test` - Run Bun tests
- `pnpm lint` / `pnpm lint:fix` - ESLint
- `pnpm format` / `pnpm format:check` - Prettier
- `pnpm type:check` - TypeScript validation

**Documentation**: See `tools/p67-cli/CLAUDE.md` for detailed CLI documentation

### 4. Native Application

**Location**: `native-app/`

**Purpose**: Snowflake Native Application configuration for deploying P67 as a native Snowflake app.

**Key Files**:
- `manifest.yml` - Application manifest (version 2 format)
- `setup.sql` - Setup scripts and stored procedures
- `README.md` - Documentation

**Features**:
- Application roles (app_admin, app_user)
- Compute pool creation and management
- Service lifecycle management (start, stop)
- Stored procedures:
  - `v1.init()` - Version initializer
  - `v1.create_services()` - Create compute pool and services
  - `v1.start_harness()` - Start harness service
  - `v1.app_url()` - Get application URL
  - `app.stop_app()` - Stop application

### 5. Deployment & Operations

#### Makefile Commands

The root `Makefile` provides key operational commands:

**Build & Deploy**:
- `make build` / `make build-harness` - Build Docker images for linux/amd64
- `make push` / `make push_harness` - Push images to Snowflake registry
- `make deploy` - Full deployment (login, build, push, run)
- `make login` - Authenticate with Snowflake registry

**Development**:
- `make dev` - Start local development with Docker Compose
- `make fix` - Fix linting and formatting issues
- `make ci` - Run CI checks (lint, format, type-check)

**Snowflake SPCS**:
- `make list` - List SPCS services
- `make describe` - Describe harness service
- `make url` - Get service ingress URL
- `make init-provider-account` - Initialize provider account

#### Docker Configuration

**Dockerfile**:
- Multi-stage build optimized for production
- Stages: base (Node.js 20 Alpine), deps, builder, runner
- Build arguments: `SERVICE_NAME`, `SERVICE_PORT`
- Supports building any service in the monorepo

**docker-compose.yaml**:
- Service: harness
- Port mapping: 3000:8000
- Volume: `.local-storage` for persistent data
- Environment: Development configuration

#### Snowflake Configuration

**snowflake.yml**: Snowflake CLI configuration
- Application package: `p67_app_pkg`
- Application instance: `p67`
- Database: `p67_src`
- Schema: `core`
- Image repository: `img_repo`
- Warehouse: `p67_provider_wh`

### 6. Scripts

The `scripts/` directory contains shell scripts for workflow operations:

**Local Operations** (interact with local Docker instance):
- `local_create_workflow.sh` - Create workflow locally
- `local_list_workflows.sh` - List local workflows
- `local_run_workflow.sh` - Run workflow locally

**SPCS Operations** (interact with Snowflake SPCS):
- `spcs_create_workflow.sh` - Create workflow on SPCS
- `spcs_list_workflows.sh` - List SPCS workflows
- `spcs_run_workflow.sh` - Run workflow on SPCS
- `spcs_healthcheck.sh` - SPCS health check
- `get_spcs_endpoint_harness.sh` - Get SPCS endpoint URL

### 7. Example Workflows

**Location**: `example_workflows/number_one/`

**Purpose**: Example LangGraph workflow demonstrating P67 workflow structure

**Technology Stack**:
- Framework: LangGraph (@langchain/langgraph 0.2.0)
- Language: TypeScript 5.3.0
- Bundler: esbuild 0.27.1

**Key Files**:
- `src/` - Workflow source code
- `package.json` - Dependencies
- `p67.yml` - P67 workflow configuration
- `build.js` - esbuild build script
- `Makefile` - Build commands

### 8. Claude Code Environment (CoCo)

**Location**: `coco/`

**Purpose**: Custom Claude Code environment for P67 development

**Contents**:
- `commands/` - Custom slash commands for Claude Code
  - `define-workflow.md` - Define workflow command
  - `generate-workflow.md` - Generate workflow command
  - `p67/utils.py` - Python utilities
- `demo/`, `demo-1/`, `demo-2/`, `demo-2ts/` - Demo project templates
- `setup.sh` - Environment setup script
- `Makefile` - Build commands

**Usage**: Run `make` in `coco/` to initialize a demo project with P67 commands

## UI Component Library

### Mantine UI

The web package uses Mantine v8 as the UI component library. Mantine provides a comprehensive set of accessible, customizable React components.

**Documentation**: https://mantine.dev/llms.txt

#### Setup
- **Provider**: MantineProvider wraps the app in `main.tsx`
- **Styles**: `@mantine/core/styles.css` imported at the top of `main.tsx`
- **PostCSS**: Configured via `postcss.config.cjs` with `postcss-preset-mantine`

#### Available Packages
- `@mantine/core` - Core components (Button, TextInput, Select, Modal, etc.)
- `@mantine/hooks` - Utility hooks (useMediaQuery, useClickOutside, etc.)

#### Usage Example
```typescript
import { Button, TextInput, Stack, Paper } from '@mantine/core';

function MyComponent() {
  return (
    <Paper p="md" shadow="sm">
      <Stack gap="md">
        <TextInput label="Name" placeholder="Enter your name" />
        <Button variant="filled" color="blue">
          Submit
        </Button>
      </Stack>
    </Paper>
  );
}
```

#### Best Practices
- Import only the components you need
- Use Mantine's spacing system (`p`, `m`, `gap` props) for consistency
- Leverage Mantine hooks for common functionality
- Use Mantine's color system for theming
- Refer to [Mantine documentation](https://mantine.dev) for component APIs

## Code Style Guidelines

### TypeScript Style
- **Always use semicolons**: All statements must end with semicolons
- **Quote style**: Use single quotes for strings
- **Trailing commas**: Always include trailing commas in multi-line structures
- **Arrow functions**: Always use parentheses around parameters
- **Indentation**: 2 spaces (no tabs)
- **Line width**: Maximum 100 characters
- **Import organization**: Imports are automatically sorted alphabetically

### Example:
```typescript
import cors from '@fastify/cors';
import Fastify from 'fastify';

const fastify = Fastify({
  logger: true,
});

await fastify.register(cors, {
  origin: true,
});

const start = async () => {
  try {
    const port = Number.parseInt(process.env.PORT) || 3001;
    await fastify.listen({ port, host: '0.0.0.0' });
    console.log(`Server listening on port ${port}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
```

### React/JSX Style
- **Component naming**: Use PascalCase for components
- **Props**: Use TypeScript interfaces for prop types
- **Hooks**: Follow React hooks rules and conventions
- **Button elements**: Always specify explicit `type` attribute
- **External links**: Use `rel="noreferrer"` with `target="_blank"`
- **Null assertions**: Avoid using non-null assertions (`!`), prefer proper null checks

## Available Scripts

### Root Level (Workspace)
- `pnpm dev` - Run all packages in development mode (parallel)
- `pnpm dev:api` - Run API service only
- `pnpm dev:web` - Run web app only
- `pnpm build` - Build all packages
- `pnpm build:api` - Build API package
- `pnpm build:web` - Build web package
- `pnpm lint` - Lint all packages
- `pnpm lint:fix` - Auto-fix linting issues across all packages
- `pnpm format` - Format code across all packages
- `pnpm format:check` - Check code formatting
- `pnpm type:check` - Type-check all packages
- `pnpm ci` - Run all CI checks in parallel (lint, format, type-check)

### Individual Packages

Each package (api, web, harness, p67-cli) has similar scripts:
- `pnpm dev` - Development mode
- `pnpm build` - Production build
- `pnpm start` - Run production build (where applicable)
- `pnpm lint` / `pnpm lint:fix` - ESLint
- `pnpm format` / `pnpm format:check` - Prettier
- `pnpm type:check` - TypeScript validation

Use `pnpm --filter <package-name>` to run scripts for specific packages:
```bash
pnpm --filter @p67/api dev
pnpm --filter @p67/harness build
pnpm --filter @p67/cli start
```

## Development Workflow

### Initial Setup
1. Install dependencies: `pnpm install`
2. Choose your development path:
   - **Full stack**: `pnpm dev` (runs API + Web)
   - **Harness service**: `make dev` (Docker Compose)
   - **CLI development**: `cd tools/p67-cli && pnpm start`

### Starting Development

**Traditional Web Development** (API + Web):
```bash
pnpm dev
# API runs on http://localhost:3001
# Web runs on http://localhost:5173
```

**Harness Service Development**:
```bash
# Local Docker development
make dev
# Harness runs on http://localhost:3000

# OR native development
cd services/harness
pnpm dev
# Harness runs on http://localhost:8000
```

**CLI Development**:
```bash
cd tools/p67-cli
pnpm start -- <command>
# Example: pnpm start -- workflow list
```

### Code Quality Workflow
1. Before committing, run: `pnpm lint:fix` to auto-fix ESLint issues
2. Run `pnpm format` to ensure consistent Prettier formatting
3. Run `pnpm type:check` to validate TypeScript
4. Or run all checks at once: `pnpm ci`

### Workflow Development Workflow

To develop and test a workflow:
1. Create your workflow in a directory (see `example_workflows/number_one/`)
2. Create `p67.yml` configuration file
3. Build your workflow: `pnpm build` (or equivalent)
4. Package as ZIP: `zip -r workflow.zip .`
5. Deploy using CLI: `p67 workflow deploy`
6. Run workflow: `p67 workflow run <workflowId>`

### Adding New Features

**To a Package**:
1. Determine which package needs changes
2. Make changes following code style guidelines
3. Run `pnpm --filter <package> lint:fix`
4. Test locally with `pnpm --filter <package> dev`
5. Run `pnpm build` to ensure production build works

**To Harness Service**:
1. Edit files in `services/harness/src/`
2. Add routes in `src/routes/` if needed
3. Update schema in `src/schema.ts` for API changes
4. Test with `make dev` or `pnpm --filter @p67/harness dev`

**To CLI**:
1. Edit or add commands in `tools/p67-cli/src/commands/`
2. Update HarnessClient if API changes needed
3. Test with `pnpm start -- <command>`

### Adding Dependencies

```bash
# Add to specific package
pnpm --filter @p67/api add <package-name>
pnpm --filter @p67/web add <package-name>
pnpm --filter @p67/harness add <package-name>
pnpm --filter @p67/cli add <package-name>

# Add as dev dependency
pnpm --filter <package> add -D <package-name>

# Update all dependencies
pnpm up -r

# Update specific package
pnpm up <package-name>
```

## ESLint and Prettier Configuration

### ESLint Configuration

Each package has its own `eslint.config.js` using the new flat config format.

**Common Configuration**:
- Extends recommended configs from ESLint and TypeScript ESLint
- TypeScript support via @typescript-eslint

**Web Package (@p67/web)**:
- React-specific plugins: `react`, `react-hooks`, `react-refresh`
- Browser globals enabled
- JSX support enabled
- React hooks rules enforced

**Backend Packages (@p67/api, @p67/harness)**:
- Node.js globals enabled
- Relaxed rules for backend development
- Allows unused parameters with `_` prefix

**CLI Package (@p67/cli)**:
- Node.js globals enabled
- Bun runtime consideration

### Prettier Configuration (`.prettierrc`)

Shared configuration at the root level:
- **Semicolons**: Always required
- **Quotes**: Single quotes
- **Trailing commas**: All (arrays, objects, parameters)
- **Arrow parens**: Always use parentheses
- **Tab width**: 2 spaces
- **Print width**: 100 characters
- **Use tabs**: false (spaces only)

### Ignored Patterns (`.prettierignore`)
- `node_modules/`
- `dist/`, `build/`, `.next/`, `bin/`
- `coverage/`
- Lock files (`pnpm-lock.yaml`, `package-lock.json`)
- Minified files (`*.min.js`, `*.min.css`)

## TypeScript Configuration

### Compiler Options (Common)
- **Target**: ES2022
- **Module**: ESNext
- **Strict mode**: Enabled
- **Module resolution**: bundler (web, cli) / node (api, harness)
- **Source maps**: Enabled
- **Declaration maps**: Enabled (libraries)

### Type Safety
- Strict null checks enabled
- No implicit any
- Unused locals/parameters checked
- No fallthrough cases in switch statements

## Debugging

### API/Harness Debugging
- Fastify/Hono loggers enabled by default
- Check console output for request logs
- Use `console.log` for debugging (appears in terminal)
- Pino structured logging in harness service

### Web Debugging
- Use browser DevTools
- Vite provides HMR (Hot Module Replacement)
- React DevTools extension recommended

### CLI Debugging
- Add `console.log` statements in command handlers
- Use Bun's built-in debugger
- Check network requests to harness service

### Docker Debugging
```bash
# View harness logs
docker compose logs -f harness

# Exec into container
docker compose exec harness sh

# Check service status
make describe
```

## Environment Variables

### API Service
- `PORT`: Server port (default: 3001)
- `NODE_ENV`: Environment (development/production)

### Web Application
- Vite environment variables prefixed with `VITE_`
- See Vite documentation for details

### Harness Service
- `PORT`: Server port (default: 8000)
- `DATA_ROOT`: Storage directory (default: `.local-storage`)
- `NODE_ENV`: Environment (development/production)

### CLI Tool
- Configuration via `p67.yml` file
- Authentication via environment or 1Password

## Best Practices for Claude Code

### When Making Changes
1. **Always run formatting**: Use `pnpm lint:fix` and `pnpm format`
2. **Maintain semicolons**: Enforced by Prettier
3. **Type safety**: Avoid `any` types, use proper TypeScript types
4. **Test locally**: Run appropriate dev script to verify
5. **Run CI checks**: `pnpm ci` before committing

### Code Organization
- Keep API routes organized in logical groups
- Follow React component best practices
- Use async/await for asynchronous operations
- Prefer functional components and hooks in React
- Use proper error handling with try/catch
- Validate inputs with Zod schemas (harness, cli)

### Monorepo Considerations
- Changes to shared types should be reflected in all packages
- Add dependencies to specific packages, not root
- Use `pnpm --filter <package>` for package-specific commands
- Root scripts use `-r` flag to run across all packages
- Workspace protocol (`workspace:*`) for internal dependencies

### Service Development
- Update OpenAPI schemas when changing harness API
- Add proper Zod validation for new endpoints
- Document new CLI commands in CLAUDE.md
- Test Docker builds before deploying to SPCS
- Update harness_spec.yaml for SPCS configuration changes

## Common Tasks

### Deploy Harness Locally
```bash
make dev
# Service runs on http://localhost:3000
```

### Deploy Harness to Snowflake SPCS
```bash
make deploy
# Or step by step:
make login
make build
make push
make run
```

### Create and Run a Workflow
```bash
# Using CLI
p67 workflow deploy
p67 workflow list
p67 workflow run <workflowId>

# Using scripts (local)
./scripts/local_create_workflow.sh path/to/workflow.zip
./scripts/local_list_workflows.sh
./scripts/local_run_workflow.sh <workflowId>

# Using scripts (SPCS)
./scripts/spcs_create_workflow.sh path/to/workflow.zip
./scripts/spcs_list_workflows.sh
./scripts/spcs_run_workflow.sh <workflowId>
```

### Build a New Workflow
```bash
# Create new directory
mkdir my-workflow
cd my-workflow

# Initialize package.json and p67.yml
npm init -y
cat > p67.yml << EOF
runtime:
  endpoint: http://localhost:3000
EOF

# Install dependencies (example with LangGraph)
npm install @langchain/langgraph

# Write your workflow code in src/
# Build and package
npm run build
zip -r ../my-workflow.zip .
```

### Add a Harness API Endpoint
1. Define schema in `services/harness/src/schema.ts` using Zod
2. Add route in `services/harness/src/routes/workflow.ts` (or new file)
3. Register route in `services/harness/src/routes/api.ts`
4. Test locally with `pnpm --filter @p67/harness dev`
5. Update CLI client if needed in `tools/p67-cli/src/clients/HarnessClient.ts`

### Update CLI Command
1. Edit command file in `tools/p67-cli/src/commands/`
2. Update HarnessClient if API changes needed
3. Test with `pnpm --filter @p67/cli start -- <command>`
4. Update CLAUDE.md documentation

## Git Integration

- Use `.gitignore` to exclude generated files
- ESLint respects ignore patterns in `eslint.config.js`
- Prettier respects patterns in `.prettierignore`
- Consider using git hooks (husky) for pre-commit checks

## Important Notes

1. **Module System**: All packages use ESM (`"type": "module"`)
2. **Node Version**: Ensure Node.js 18+ (20+ recommended)
3. **Package Manager**: Must use pnpm, not npm or yarn
4. **Runtime Requirements**: Bun required for CLI development
5. **Port Conflicts**: Ensure required ports are available:
   - 3001 (API)
   - 5173 (Web)
   - 8000 (Harness native)
   - 3000 (Harness Docker)
6. **Semicolons**: Always include semicolons in TypeScript/JavaScript
7. **Docker Platform**: Build for linux/amd64 when deploying to SPCS
8. **Snowflake Access**: SPCS deployment requires Snowflake account

## Resources

### Frameworks & Libraries
- Fastify Documentation: https://fastify.dev
- Hono Documentation: https://hono.dev
- React Documentation: https://react.dev
- Vite Documentation: https://vite.dev
- Mantine UI Documentation: https://mantine.dev
- LangGraph Documentation: https://langchain.com/langgraph
- Commander.js Documentation: https://github.com/tj/commander.js
- Inquirer Documentation: https://github.com/SBoudrias/Inquirer.js
- Zod Documentation: https://zod.dev

### Development Tools
- ESLint Documentation: https://eslint.org
- TypeScript ESLint: https://typescript-eslint.io
- Prettier Documentation: https://prettier.io
- TypeScript Documentation: https://www.typescriptlang.org
- pnpm Documentation: https://pnpm.io
- Bun Documentation: https://bun.sh

### Infrastructure
- Docker Documentation: https://docs.docker.com
- Snowflake Documentation: https://docs.snowflake.com
- Snowflake SPCS: https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview
- Snowflake Native Apps: https://docs.snowflake.com/en/developer-guide/native-apps/overview
