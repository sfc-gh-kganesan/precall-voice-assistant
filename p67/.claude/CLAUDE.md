# Project: P67 (Cortex Mesh)

## What this is
A TypeScript monorepo for building, testing, and deploying agentic workflows on Snowflake. Combines a React frontend, Fastify APIs, and a workflow control plane service that runs on Snowflake SPCS.

## Architecture
- `packages/api` - Fastify backend API (port 3001)
- `packages/web` - React + Mantine UI frontend (port 5173)
- `services/controld` - Workflow control plane service (port 3002)
- `tools/p67-cli` - CLI for workflow management (Bun runtime)
- `native-app/` - Snowflake Native Application config
- `example_workflows/` - Sample LangGraph workflows

## Common tasks

### Development
```bash
pnpm install          # Install dependencies
pnpm dev              # Run API + Web
make dev              # Run controld via Docker
```

### Code quality
```bash
pnpm fix              # Auto-fix linting/formatting (Biome)
pnpm check            # Verify code quality
pnpm type:check       # TypeScript validation
pnpm ci               # Run all checks
```

### Workflow operations
```bash
p67 workflow deploy   # Deploy workflow ZIP
p67 workflow list     # List workflows
p67 workflow run <id> # Execute workflow
```

### Deployment
```bash
make deploy           # Full SPCS deployment (login, build, push, run)
make build            # Build Docker image
make push             # Push to Snowflake registry
```

## Conventions
- **Semicolons**: Always required
- **Quotes**: Single quotes for strings
- **Indentation**: 2 spaces (tabs in Biome config)
- **Line width**: 100 characters max
- **Trailing commas**: Always include
- **Module system**: ESM (`"type": "module"`)
- **Package manager**: pnpm only (not npm/yarn)
- **Tooling**: Biome for linting/formatting (replaces ESLint/Prettier)

## Tech stack
- Frontend: React 19, Vite 7, Mantine v8, TypeScript
- Backend: Fastify 5, Node.js, Zod validation
- CLI: Bun, Commander.js
- Infra: Docker, Snowflake SPCS
