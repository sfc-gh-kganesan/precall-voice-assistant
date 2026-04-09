# Controld Service

Control plane service for P67 platform.

## Overview

Controld is a TypeScript-based microservice built with the Fastify web framework. It provides a high-performance API with automatic OpenAPI documentation generation and Swagger UI integration using Zod for type-safe validation. It manages workflow deployment, execution, secrets, OAuth tokens, logs, and Human-in-the-Loop (HITL) interrupts.

## Technology Stack

- **Runtime**: Node.js with ESM modules
- **Framework**: Fastify 5.2.0 (fast, low-overhead web framework)
- **API Documentation**: @fastify/swagger, @fastify/swagger-ui
- **Type Provider**: fastify-type-provider-zod
- **Validation**: Zod 3.23.8 for schema validation
- **Database**: PostgreSQL via Prisma (`@p67/db`)
- **Language**: TypeScript 5.9.3
- **Target**: ES2022

## Getting Started

### Prerequisites

- Node.js 20+
- pnpm 10.22.0+
- PostgreSQL (via Docker Compose for local dev)

### Installation

From the project root:

```bash
pnpm install
```

### Development

Start the development server with hot reload:

```bash
pnpm dev
```

The service will start on `http://localhost:3002` by default.

Alternatively, start all services (including Postgres) via Docker Compose from the repo root:

```bash
docker compose up
```

### Build

Compile TypeScript to JavaScript:

```bash
pnpm build
```

### Production

Run the compiled production build:

```bash
pnpm start
```

## API Documentation

Once the service is running, you can access:

- **Swagger UI**: http://localhost:3002/docs
- **OpenAPI Schema**: http://localhost:3002/docs/json

## Available Endpoints

### Health Check

- **GET** `/api/health` - Returns service health status

```json
{
  "status": "ok",
  "timestamp": "2025-12-13T10:00:00.000Z",
  "localStoragePath": "/path/to/storage"
}
```

### Workflows

- `POST /api/workflow/create` - Upload a workflow ZIP
- `GET /api/workflow/list` - List all workflows
- `GET /api/workflow/by-name/:name` - Get workflow by name
- `DELETE /api/workflow/:workflowId` - Delete a workflow
- `GET /api/workflow/:workflowId/manifest` - Get workflow manifest
- `GET /api/workflow/:workflowId/graph` - Get workflow graph
- `PATCH /api/workflow/:workflowId/visibility` - Set workflow visibility
- `GET /api/workflow/:workflowId/versions` - List workflow versions
- `POST /api/workflow/:workflowId/run` - Execute a workflow
- `GET /api/workflow/:workflowId/run/:runId` - Get run status
- `GET /api/workflow/:workflowId/run/:runId/interrupt` - List interrupts
- `POST /api/workflow/:workflowId/run/:runId/interrupt/:interruptId/resume` - Resume a HITL interrupt

### Secrets

- `POST /api/secret` - Save a secret
- `GET /api/secret` - List secrets
- `DELETE /api/secret/:secretId` - Delete a secret
- `GET /api/secret/:secretId` - Get a secret
- `POST /api/secret/:secretId/refresh` - Refresh an OAuth token

### Auth & Identity

- `GET /api/auth/google/callback` - Google OAuth callback
- `GET /api/whoami` - Get current user info

### Logs

- `GET /api/log` - List structured execution logs

### Webhooks

- `POST /api/webhook` - Incoming webhook endpoint (e.g. Slack)

## Project Structure

```
controld/
├── src/
│   ├── index.ts              # Main entry point (Fastify + Slack Socket Mode)
│   ├── server.ts             # Server factory (buildServer)
│   ├── config.ts             # Service configuration
│   ├── schema.ts             # Zod validation schemas
│   └── routes/
│       ├── api.ts            # Main API plugin (registers all sub-routes)
│       ├── health.ts         # Health check route
│       ├── auth.ts           # Google OAuth routes
│       ├── whoami.ts         # Current user route
│       ├── log/              # Log routes
│       ├── secret/           # Secret management routes
│       ├── webhook/          # Webhook routes (Slack, etc.)
│       └── workflow/         # Workflow routes (CRUD, run, interrupt, etc.)
├── dist/                     # Compiled output (generated)
├── package.json              # Dependencies and scripts
├── tsconfig.json             # TypeScript configuration
└── .gitignore                # Git ignore patterns
```

## Import Paths

This project uses **absolute imports** via TypeScript path aliases for cleaner, more maintainable code.

### Path Alias Configuration

All imports use the `@controld/*` alias pattern, configured in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "baseUrl": "./",
    "paths": {
      "@controld/*": ["src/*"]
    }
  }
}
```

### Import Examples

```typescript
// Instead of relative imports:
import { HealthResponseSchema } from '../schema.js';
import { GoogleOAuthClient } from '../lib/oauth/google-client.js';
import health from './health.js';

// Use absolute imports:
import { HealthResponseSchema } from '@controld/schema.js';
import { GoogleOAuthClient } from '@controld/lib/oauth/google-client.js';
import health from '@controld/routes/health.js';
```

### How It Works

**Development Mode (`pnpm dev`)**
- Uses `tsx` which natively supports TypeScript path aliases
- No transformation needed - imports work directly

**Production Mode (`pnpm build` + `pnpm start`)**
- TypeScript compiler (`tsc`) compiles `.ts` to `.js`
- `tsc-alias` transforms path aliases to relative paths in compiled output
- Node.js runs the transformed code with standard relative imports

**Note**: All imports must include the `.js` extension (ESM requirement), even when importing `.ts` files during development.

## Scripts

- `pnpm dev` - Start development server with hot reload (tsx watch)
- `pnpm build` - Compile TypeScript to JavaScript and transform path aliases
- `pnpm start` - Run production server
- `pnpm check` - Run Biome linting and formatting checks
- `pnpm fix` - Auto-fix Biome linting and formatting issues
- `pnpm type:check` - Validate TypeScript types
- `pnpm test` - Run Vitest tests

## Configuration

### Environment Variables

- `PORT` - Server port (default: 3002)
- `NODE_ENV` - Environment mode (default: development)
- `DATABASE_URL` - PostgreSQL connection string
- `ENCRYPTION_KEY` - Key for encrypting secrets at rest
- `DEBUG_ENABLE_DEFAULT_USER` - Enable a default debug user (development only)
- `SLACK_APP_TOKEN` - Slack app-level token (Socket Mode)
- `SLACK_BOT_TOKEN` - Slack bot token
- `P67_RUNNER_IMAGE` - Docker image for spawning workflow runner containers
- `P67_HOST_STORAGE_ROOT` - Host path for workflow storage (Docker volume mount)
- `SNOWFLAKE_WEBHOOK_SECRET` - Shared secret for validating Snowflake webhook calls

### Example .env file

```bash
PORT=3002
NODE_ENV=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/controld_dev
ENCRYPTION_KEY=<random-secret>
```

## Development Workflow

### Adding New Routes

1. Create a new route plugin file in `src/routes/`
2. Define Zod schemas in `src/schema.ts`
3. Use Fastify's plugin pattern with type-safe schemas
4. Register the route in `src/routes/api.ts`

### Example Route Plugin

```typescript
import { FastifyPluginAsync } from 'fastify';
import { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';

const MyResponseSchema = z.object({
    message: z.string(),
});

const myRoute: FastifyPluginAsync = async (server) => {
    const fastify = server.withTypeProvider<ZodTypeProvider>();

    fastify.get(
        '/',
        {
            schema: {
                tags: ['MyTag'],
                summary: 'My endpoint',
                description: 'Description of my endpoint',
                response: {
                    200: MyResponseSchema,
                },
            },
        },
        async () => {
            return { message: 'Hello' };
        },
    );
};

export default myRoute;
```

## Code Quality

This project uses **Biome** as a unified toolchain for linting and formatting.

Run checks before committing:

```bash
pnpm check       # Lint and format check
pnpm fix         # Auto-fix issues
pnpm type:check  # TypeScript validation
```

## Architecture

### Fastify Features

- **Built-in Logging** - Pino logger integrated by default
- **Type Safety** - Full TypeScript support with Zod schemas
- **Plugin System** - Modular architecture using Fastify plugins
- **CORS** - Cross-origin resource sharing via @fastify/cors
- **Validation** - Automatic request/response validation with Zod
- **Performance** - One of the fastest Node.js web frameworks

### OpenAPI Integration

The service uses `fastify-type-provider-zod` and `@fastify/swagger` for:

- Automatic OpenAPI 3.1.0 schema generation from Zod schemas
- Runtime request/response validation
- TypeScript type inference from schemas
- Interactive Swagger UI documentation

### Workflow Execution

Workflows are executed by spawning isolated child processes (locally) or running `EXECUTE JOB SERVICE` on Snowflake SPCS. The parent process and child communicate via NDJSON messages over stdin/stdout. The `runnerRegistry` on the server instance tracks live runs for HITL interrupt/resume.

### Human-in-the-Loop (HITL)

A running workflow can pause mid-execution by sending an `Interrupt` message. The run status becomes `interrupted`. A caller can then `POST .../interrupt/:interruptId/resume` with a response payload to unblock the workflow and let it continue.

## Contributing

1. Create a new branch for your feature
2. Make changes following the existing code style
3. Run `pnpm fix` before committing
4. Ensure all type checks pass with `pnpm type:check`
5. Test your changes with `pnpm dev`

## Related Services

- **Web** (`p67/packages/web`) - React frontend application
- **workflow-sdk** (`p67/packages/workflow-sdk`) - TypeScript SDK for workflow authors
- **db** (`p67/packages/db`) - Prisma database client

## Resources

- [Fastify Documentation](https://fastify.dev/)
- [Fastify Type Provider Zod](https://github.com/turkerdev/fastify-type-provider-zod)
- [Fastify Swagger](https://github.com/fastify/fastify-swagger)
- [Zod Documentation](https://zod.dev/)
