# InvoiceIQ

AI-powered invoice processing and validation system built on Snowflake and Snowpark Container Services (SPCS).

## Services

- **Dashboard** - React frontend with Express proxy for internal SPCS communication
- **Backend** - FastAPI REST API for invoice management
- **Collector** - Email-based invoice ingestion service
- **Agent** - AI agent for intelligent invoice processing (future)

## Quick Start

### Prerequisites

- Snowflake account with SPCS enabled
- Docker
- Snowflake CLI (`snow`)

### Deployment

1. **Setup Snowflake**:
   ```bash
   # Run initialization scripts
   snow sql -f snowflake/init_snowflake_db.sql
   snow sql -f snowflake/init_snowflake_spcs.sql
   ```

2. **Deploy Services**:
   ```bash
   # Backend
   cd backend/release && ./build_and_deploy.sh
   
   # Dashboard
   cd ui/dashboard/release && ./build_and_deploy.sh
   
   # Collector
   cd collector/release && ./build_and_deploy.sh
   ```

3. **Access Dashboard**:
   ```bash
   cd ui/dashboard/scripts
   ./get_spcs_endpoint.sh
   ```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design decisions
- [SOLUTION_FINAL.md](SOLUTION_FINAL.md) - Solution summary
- [ui/dashboard/DEPLOYMENT.md](ui/dashboard/DEPLOYMENT.md) - Dashboard deployment guide
- [backend/README.md](backend/README.md) - Backend API documentation
- [collector/README.md](collector/README.md) - Collector service documentation

## Key Features

- ✅ Internal SPCS networking (no OAuth complexity)
- ✅ SPCS session token authentication to Snowflake
- ✅ Real-time invoice status updates
- ✅ PDF viewing and downloading
- ✅ Bulk invoice operations
- ✅ Email-based invoice ingestion

## Development

Each service can be run locally for development:

```bash
# Backend
cd backend && uv sync && uv run uvicorn app.main:app --reload

# Dashboard
cd ui/dashboard && npm install && npm run dev

# Collector
cd collector && uv sync && uv run uvicorn app.main:app --reload
```

## Support

For issues or questions, see the troubleshooting sections in:
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ui/dashboard/DEPLOYMENT.md](ui/dashboard/DEPLOYMENT.md)
