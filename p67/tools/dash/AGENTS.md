# Dashboard (tools/dash) - Agent Instructions

## Pre-commit Checks

Before committing any changes to this project, **always** run these checks and fix any errors:

```bash
cd tools/dash

# 1. TypeScript type check (includes vite config + app source)
npx tsc -b

# 2. Biome lint + format (run from repo root)
cd ../.. && npx @biomejs/biome check --write --unsafe tools/dash/ services/controld/src/routes/workflow/
# Then verify: npx @biomejs/biome check tools/dash/ services/controld/src/routes/workflow/

# 3. Build (runs tsc -b + vite build)
cd tools/dash && pnpm build
```

Biome is configured at the repo root (`biome.json`): 4-space indent, single quotes, sorted imports, `node:` protocol for Node.js builtins. CI runs `biome check` across the monorepo.

## Dev Server

```bash
# Default: proxies /api/* to local controld at http://localhost:3002
pnpm dev

# Mock mode (no backend needed):
MOCK_API=1 pnpm dev

# Custom backend:
API_TARGET=https://<url>.snowflakecomputing.app pnpm dev
```

Dev server runs on port 3001.

## Project Conventions

- React 18 + TypeScript, Vite 6, pnpm
- UI: Snowflake Stellar Components (`@snowflake/stellar-components`)
- Styling: StyleX (`@stylexjs/stylex`)
- State: TanStack Query (`@tanstack/react-query`)
- Routing: React Router DOM
- Graph viz: React Flow (`@xyflow/react`) + dagre for layout
- Path alias: `@/` maps to `src/`
- No comments in code unless explicitly requested
- `tsconfig.node.json` covers vite config files; `tsconfig.json` covers `src/`

## Key Files

- `vite.config.ts` - Dev server config, API proxy/mock toggle
- `dev-mock-plugin.ts` - Mock API data for offline frontend dev
- `src/api/client.ts` - API client (all calls to `/api/*`)
- `src/components/WorkflowGraph/` - React Flow graph visualization
- `server/server.js` - Express server for SPCS deployment (NOT used in dev)
