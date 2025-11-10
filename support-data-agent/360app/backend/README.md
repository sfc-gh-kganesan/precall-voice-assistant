# Backend

FastAPI backend with Snowpark DataFrame API.

## Development

```bash
cd backend
uv sync
uv run dev-server
```

## API Endpoints

**Health:**
- `GET /health`
- `GET /ready`

**Dashboard:**
- `GET /api/v1/dashboard/kpis`
- `GET /api/v1/dashboard/products`
- `GET /api/v1/dashboard/topics`

**Admin:**
- `GET /api/v1/admin/databases`
- `GET /api/v1/admin/schemas`
- `GET /api/v1/admin/tables`
- `POST /api/v1/admin/configurations`
- `GET /api/v1/admin/configurations`

**Schema:**
- `GET /admin/schema/status`
- `POST /admin/schema/initialize`
- `POST /admin/schema/clean`
- `POST /admin/schema/reset`

**AI Enrichment:**
- `POST /admin/enrich/{configId}`
- `GET /admin/jobs/{jobId}`

**Data:**
- `GET /api/v1/tickets`
- `POST /api/v1/chat/messages`
