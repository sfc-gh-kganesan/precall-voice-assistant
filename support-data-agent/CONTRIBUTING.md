# Contributing

## Setup

**Prerequisites:**
- Docker Desktop
- Python 3.11+ (optional, for local dev)
- Node.js 18+ (optional, for local dev)

**Quick start:**
```bash
docker compose up -d
```

**Local development:**
```bash
# Backend
cd backend && uv sync && uv run dev-server

# Frontend
cd frontend && npm install && npm run dev
```

## Schema Management

**Initialize schema:**
```bash
# With sample data
curl -X POST "http://localhost:8000/admin/schema/initialize?include_sample_data=true"

# Clean (production)
curl -X POST "http://localhost:8000/admin/schema/initialize"

# Reset everything
curl -X POST "http://localhost:8000/admin/schema/reset"
```

**CLI commands:**
```bash
cd backend
uv run initialize-schema --with-samples
uv run initialize-schema --clean
uv run initialize-schema --reset
```

## Code Quality

```bash
# Backend
uvx ruff check --fix && uvx ruff format

# Frontend
cd frontend && npm run lint && npm run format
```

## Environment

**Backend (.env):**
```
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_AUTHENTICATOR=your_password
SNOWFLAKE_DATABASE=your_database
```

## Docker

```bash
# Rebuild
docker compose up --build

# Logs
docker compose logs -f backend

# Clean restart
docker compose down -v --remove-orphans && docker compose up
```

## Testing

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm test

# CI workflow
act -W .github/workflows/support-data-agent-ci.yml
```
