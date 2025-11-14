# Project 67

Experimental platform for building, testing, and deploying agentic workflows.

## Project Structure

```
.
├── packages/
│   ├── api/          # Fastify backend API
│   └── web/          # React 19 + Vite frontend
├── package.json
└── pnpm-workspace.yaml
```

## Tech Stack

- **Backend (packages/api):**
  - TypeScript
  - Fastify
  - Node.js

- **Frontend (packages/web):**
  - React 19
  - TypeScript
  - Vite
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

The backend API runs on `http://localhost:3001` and includes:

- `GET /api/health` - Health check endpoint
- `GET /api/hello` - Sample API endpoint

## Frontend

The frontend runs on `http://localhost:5173` during development.
