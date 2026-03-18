# p67-dash

Dashboard UI for P67 workflow management.

## Overview

A React-based dashboard built with Snowflake's Stellar design system for managing P67 workflows, runs, and human-in-the-loop interrupts.

## Technology Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 6
- **UI Components**: Snowflake Stellar Components
- **State Management**: TanStack Query (React Query)
- **Routing**: React Router DOM
- **Styling**: StyleX

## Local Development

### Prerequisites

- Node.js 20+
- pnpm 10+
- Docker (for Postgres)

### Quick Start

1. **Start Postgres** (from p67 root):
   ```bash
   cd /path/to/p67
   docker compose up -d postgres
   ```

2. **Set up controld environment**:
   ```bash
   cd services/controld
   cp .env.example .env
   
   # Generate and set encryption key
   openssl rand -base64 32
   # Edit .env and set ENCRYPTION_KEY=<generated key>
   ```

3. **Initialize database**:
   ```bash
   cd packages/db
   DATABASE_URL="postgresql://postgres:password@localhost:5432/controld_dev?schema=public" pnpm exec prisma db push
   DATABASE_URL="postgresql://postgres:password@localhost:5432/controld_dev?schema=public" pnpm exec prisma generate
   pnpm build
   ```

4. **Start controld** (Terminal 1):
   ```bash
   cd services/controld
   pnpm dev
   ```
   Runs on http://localhost:3002

5. **Start dash** (Terminal 2):
   ```bash
   cd tools/dash
   pnpm dev
   ```
   Runs on http://localhost:3001

### API Configuration

By default, the dev server proxies `/api/*` requests to local controld at `http://localhost:3002`.

| Variable | Default | Description |
|----------|---------|-------------|
| `API_TARGET` | `http://localhost:3002` | Backend URL to proxy `/api/*` requests to. |
| `MOCK_API` | _(unset)_ | Set to `1` to use the mock API plugin instead of proxying. |

**Default** (proxy to local controld):
```bash
pnpm dev
```

**Proxy to SPCS**:
```bash
API_TARGET=https://<ingress-url>.snowflakecomputing.app pnpm dev
```

**Mock mode** (no backend needed):
```bash
MOCK_API=1 pnpm dev
# Serves fake data from dev-mock-plugin.ts
# Includes test workflows: with_interrupt, number_one, decision_demo, no_graph, auto_extracted
```

## Project Structure

```
dash/
├── src/
│   ├── api/
│   │   ├── client.ts         # API client functions
│   │   └── types.ts          # TypeScript types
│   ├── components/
│   │   ├── AppShell.tsx      # Main layout
│   │   └── BaltoThemeWrapper.tsx
│   ├── hooks/
│   │   ├── useWorkflows.ts   # Workflow queries/mutations
│   │   ├── useRuns.ts        # Run queries
│   │   ├── useLogs.ts        # Log queries
│   │   └── useInterrupts.ts  # Interrupt queries/mutations
│   ├── pages/
│   │   ├── WorkflowsPage.tsx
│   │   ├── WorkflowDetailPage.tsx
│   │   ├── RunDetailPage.tsx
│   │   └── InterruptsPage.tsx
│   ├── App.tsx
│   └── main.tsx
├── spec/
│   └── openapi.yaml          # API specification
├── native-app/               # SPCS deployment configs
│   ├── Dockerfile
│   ├── manifest.yml
│   └── service_spec.yaml
├── vite.config.ts
└── package.json
```

## Features

- **Workflows**: List, run, delete workflows; manage visibility (Public/Private)
- **Runs**: View run history, logs, and execution details
- **Interrupts**: Human-in-the-loop approval queue; resume paused workflows
- **Real-time Updates**: Polling-based refresh (10 second intervals)

## Available Scripts

- `pnpm dev` - Start development server
- `pnpm build` - Build for production
- `pnpm preview` - Preview production build
- `pnpm lint` - Run ESLint

## Deployment

For SPCS deployment, see `native-app/` directory for Docker and manifest configurations.

## Related

- [controld service](../../services/controld/README.md) - Backend API
- [P67 docs](../../README.md) - Platform overview
