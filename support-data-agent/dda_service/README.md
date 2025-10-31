# FDE DDA Service

Frontend-Decoupled Diagnostic Data Application (DDA) API Service

## Overview

This is a FastAPI-based backend service that provides a REST API for Snowflake diagnostic data operations. It decouples all business logic, data access, and query execution from the monolithic Streamlit application.

### Key Features

- **Frontend-Agnostic REST API**: Can be consumed by any client (Streamlit, React, CLI tools, etc.)
- **Query-First Architecture**: Complete Query view implementation with 18+ endpoints
- **Environment-Based Data Masking**: Automatic table/view routing to protect customer data in dev/local
- **In-Memory Caching**: 15-minute TTL cache for improved performance (MVP)
- **Simple API Key Authentication**: Secure API access for MVP (OAuth2 + JWT in Phase 2)
- **Snowflake Connection Pooling**: Efficient database connection management
- **Auto-Generated API Documentation**: OpenAPI/Swagger docs at `/api/docs`

## Architecture

```
fde_dda_service/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Pydantic settings
│   ├── dependencies.py         # Dependency injection (auth, etc.)
│   ├── api/v1/endpoints/       # REST API endpoints
│   ├── core/                   # Core modules (database, cache, etc.)
│   ├── services/               # Business logic layer
│   ├── queries/                # SQL query definitions
│   ├── models/                 # Pydantic request/response models
│   └── utils/                  # Utilities (table_mappings, etc.)
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
└── .env.example                # Environment configuration template
```

## Quick Start

### Prerequisites

- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- Snowflake account credentials
- API key for authentication

### Installation

1. **Install uv** (if not already installed):
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

2. **Clone the repository** (if not already in the repo):
```bash
cd /path/to/cxe-dda-streamlit/dda_service
```

3. **Install dependencies**:
```bash
uv sync
```

This will automatically create a virtual environment and install all dependencies.

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your Snowflake credentials and API key
```

Required environment variables:
- `SNOWFLAKE_ACCOUNT`: Your Snowflake account (e.g., "snowhouse")
- `SNOWFLAKE_USER`: Service account username
- `SNOWFLAKE_PASSWORD`: Service account password
- `API_KEY`: Secret key for API authentication
- `ENV`: Environment (local/dev/canary/prod)

### Running Locally

```bash
# Development mode with auto-reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- API Base: `http://localhost:8000`
- Swagger Documentation: `http://localhost:8000/api/docs`
- ReDoc Documentation: `http://localhost:8000/api/redoc`
- OpenAPI Spec: `http://localhost:8000/api/openapi.json`

### Testing the API

```bash
# Health check (no auth required)
curl http://localhost:8000/health

# Get query metadata (requires API key)
curl -H "X-API-Key: your_api_key_here" \
     http://localhost:8000/api/v1/queries/01abc-123
```

## API Usage

### Authentication

All API endpoints require an API key in the request header:

```bash
X-API-Key: your_api_key_here
```

Example with curl:
```bash
curl -H "X-API-Key: your_api_key_here" \
     http://localhost:8000/api/v1/queries/{query_id}
```

Example with Python:
```python
import requests

headers = {"X-API-Key": "your_api_key_here"}
response = requests.get(
    "http://localhost:8000/api/v1/queries/01abc-123",
    headers=headers
)
data = response.json()
```

### Available Endpoints

#### Query Endpoints (Primary - Fully Implemented)

- `GET /api/v1/queries/{query_id}` - Get comprehensive query metadata
- `GET /api/v1/queries/{query_id}/historical-runs` - Historical runs
- `GET /api/v1/queries/{query_id}/concurrent` - Concurrent queries
- `GET /api/v1/queries/{query_id}/logs/gs` - Global Services logs
- `GET /api/v1/queries/{query_id}/logs/xp` - Execution Platform logs
- `GET /api/v1/queries/{query_id}/parameters` - Non-default parameters
- `GET /api/v1/queries/{query_id}/incidents` - Related incidents
- `GET /api/v1/queries/{query_id}/parent-child` - Query execution tree
- `GET /api/v1/queries/{query_id}/processing-status` - DDA pipeline status
- `POST /api/v1/queries/adhoc-process` - Trigger adhoc processing
- `POST /api/v1/queries/compare` - Compare two queries
- Additional query operations...

#### Other Endpoints (Basic GET operations)

- `GET /api/v1/accounts/{id}` - Get account metadata
- `GET /api/v1/cases/{id}` - Get case information
- `GET /api/v1/warehouses/{id}` - Get warehouse details
- `GET /api/v1/snowpipes/{id}` - Get snowpipe information
- `GET /api/v1/parameters/{name}` - Get parameter details
- `GET /api/v1/tsw/*` - Troubleshooting workflow endpoints
- `POST /api/v1/search` - Universal search
- `GET /api/v1/landing-page` - Landing page data

Full API documentation available at `/api/docs` when the server is running.

## Environment Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENV` | Environment (local/dev/canary/prod) | local | No |
| `SNOWFLAKE_ACCOUNT` | Snowflake account name | - | Yes |
| `SNOWFLAKE_USER` | Service account username | - | Yes |
| `SNOWFLAKE_PASSWORD` | Service account password | - | Yes |
| `SNOWFLAKE_WAREHOUSE` | Warehouse name | DDA_WH | No |
| `SNOWFLAKE_DATABASE` | Database name | SUPPORT | No |
| `SNOWFLAKE_SCHEMA` | Schema name | CXE | No |
| `SNOWFLAKE_ROLE` | Role name | DDA_ROLE | No |
| `API_KEY` | API authentication key | - | Yes |
| `CACHE_ENABLED` | Enable in-memory caching | true | No |
| `CACHE_TTL_SECONDS` | Cache TTL in seconds | 900 | No |
| `CACHE_MAX_SIZE` | Max cache entries | 1000 | No |
| `QUERY_TIMEOUT_SECONDS` | Query timeout | 300 | No |
| `MAX_QUERY_RESULTS` | Max result rows | 10000 | No |

### Table/View Mappings

**CRITICAL**: The service automatically routes queries to masked views in dev/local environments to protect customer data.

- **dev/local**: Uses `*_MASKED_V` views for all customer data tables
- **canary/prod**: Uses production tables directly

This is handled automatically by `app/utils/table_mappings.py`.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/test_api/test_queries.py
```

### Code Formatting

```bash
# Format code
uv run black app/

# Lint
uv run flake8 app/

# Type checking
uv run mypy app/
```

## Deployment

### Docker

```bash
# Build image
docker build -t fde-dda-service:latest .

# Run container
docker run -p 8000:8000 --env-file .env fde-dda-service:latest
```

### Docker Compose (Local Development)

```bash
docker-compose up -d
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests (coming in Phase 4).

## Monitoring

### Health Checks

- `/health` - Basic health check (always returns 200 if service is running)
- `/ready` - Readiness check (checks dependencies)

### Logging

Logs are output to stdout in structured format:
```
2024-01-15 10:30:45 - app.main - INFO - Starting fde-dda-service in local environment
```

### Cache Statistics

Get cache performance metrics:
```bash
# Future endpoint (Phase 2)
curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/admin/cache/stats
```

## Roadmap

### MVP (Current - Week 1-4)
- ✅ FastAPI foundation
- ✅ Simple API key authentication
- ✅ In-memory caching
- ✅ Snowflake connection pooling
- ✅ Table/view mappings (dev/prod)
- ✅ Query view (full implementation)
- ⏳ Basic endpoints for other views
- ⏳ Docker deployment

### Phase 2 (Post-MVP)
- ⏳ OAuth2 + JWT authentication
- ⏳ Redis distributed caching
- ⏳ Full CRUD operations for all views
- ⏳ JIRA integration
- ⏳ Comprehensive test coverage
- ⏳ Prometheus metrics
- ⏳ Advanced monitoring

## Troubleshooting

### Common Issues

**Connection refused**:
- Ensure Snowflake credentials are correct in `.env`
- Check network connectivity to Snowflake
- Verify warehouse/database/schema names

**Authentication failed**:
- Verify `API_KEY` in `.env` matches request header
- Check `X-API-Key` header is properly set

**Query returns empty results**:
- In dev/local, ensure masked views exist for the table
- Check `ENV` variable is set correctly
- Verify query parameters are correct

### Logs

View application logs:
```bash
# If running locally
# Logs output to stdout

# If running in Docker
docker logs <container_id>

# If running in Kubernetes
kubectl logs -f deployment/fde-dda-service -n dda
```

## Support

For issues or questions:
1. Check `/api/docs` for API documentation
2. Review logs for error messages
3. Consult `REFACTOR_BACKEND_ONLY.txt` for architecture details
4. Contact the Customer Experience Engineering team

## License

Internal Snowflake project - not for external distribution.
