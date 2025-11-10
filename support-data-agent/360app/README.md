## Support Data Agent

Analytics dashboard for Snowflake support case data with AI classification.

## Quick Start

```bash
cd support-data-agent
docker compose up -d
```

**Configure Snowflake** (create `backend/.env`):
```
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=your_database
```

**Initialize schema:**
```bash
curl -X POST "http://localhost:8000/admin/schema/initialize"
```

**Access:**
- Dashboard: http://localhost:3000
- API: http://localhost:8000

## What it does

1. Connects to your Snowflake support case data
2. Uses Snowflake Cortex AI to classify cases by topic/product
3. Creates analytics tables for dashboard queries
4. Shows trends, resolution rates, and insights

## Stack

- Backend: FastAPI + Snowpark DataFrame API
- Frontend: Next.js dashboard
- Database: Snowflake + Cortex AI
- Deploy: Docker

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.
