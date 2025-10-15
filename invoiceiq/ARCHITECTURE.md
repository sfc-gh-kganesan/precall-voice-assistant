# InvoiceIQ Architecture

## Overview

InvoiceIQ is a Snowflake-native invoice processing and validation system deployed on Snowpark Container Services (SPCS).

## Services

### 1. Dashboard (Frontend + Proxy)
- **Technology**: React + Express
- **Port**: 3000
- **Public Endpoint**: Yes
- **Purpose**: 
  - Serves React frontend to users
  - Proxies API requests to backend via internal SPCS networking

**Key Feature**: Express proxy server handles all API calls internally, eliminating the need for OAuth tokens in frontend code.

```javascript
// server.js proxies /api/* to backend
app.use('/api', createProxyMiddleware({
  target: 'http://backend.ivzu.svc.spcs.internal:8001',
  pathRewrite: { '^/api': '' }
}));
```

### 2. Backend (API)
- **Technology**: FastAPI + Python
- **Port**: 8001
- **Internal Endpoint**: `http://backend.ivzu.svc.spcs.internal:8001`
- **Purpose**: REST API for invoice management
- **Authentication**: Uses SPCS OAuth session token to connect to Snowflake

**Key Endpoints**:
- `GET /invoices` - List invoices with filtering
- `GET /invoices/{ticket}/view` - View PDF
- `GET /invoices/{ticket}/download` - Download PDF
- `PATCH /invoices/status` - Update invoice status

### 3. Collector (File Ingestion)
- **Technology**: FastAPI + Python
- **Port**: 8000
- **Public Endpoint**: Yes (for email integration)
- **Purpose**: Receives invoice files and metadata from email system

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Users                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS (OAuth)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Dashboard Container (SPCS)                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Express Proxy Server (port 3000)                           │ │
│  │  - Serves React static files                               │ │
│  │  - Proxies /api/* → backend                                │ │
│  └────────────────────┬───────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                         │ Internal SPCS Network
                         │ (No auth required!)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend Container (SPCS)                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ FastAPI (port 8001)                                        │ │
│  │  - Invoice CRUD operations                                 │ │
│  │  - PDF viewing/downloading                                 │ │
│  └────────────────────┬───────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                         │ OAuth Session Token
                         │ (from /snowflake/session/token)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Snowflake Database                            │
│  - INVOICES table                                                │
│  - TICKET_METADATA table                                         │
│  - TICKET_ATTACHMENTS stage                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Authentication Flow

### 1. User → Dashboard
- **Method**: Snowflake OAuth
- **When**: Accessing dashboard public endpoint
- **Handled by**: SPCS ingress (automatic)

### 2. Dashboard → Backend
- **Method**: None (internal SPCS networking)
- **When**: API calls from browser
- **Flow**:
  1. Browser calls `/api/invoices`
  2. Express proxy forwards to `http://backend.ivzu.svc.spcs.internal:8001/invoices`
  3. No authentication needed (internal network)

### 3. Backend → Snowflake
- **Method**: OAuth with SPCS session token
- **When**: Database queries
- **Code**:
  ```python
  if os.path.isfile("/snowflake/session/token"):
      config = {
          "authenticator": "oauth",
          "token": open("/snowflake/session/token").read(),
          ...
      }
  ```

## Key Design Decisions

### Why Express Proxy in Frontend Container?

**Problem**: Browser JavaScript can't reach internal SPCS DNS names.

**Solution**: Integrate proxy server into frontend container:
- ✅ Leverages internal SPCS networking
- ✅ No OAuth complexity in application code
- ✅ Fast, low-latency communication
- ✅ Secure (never leaves SPCS network)

**Alternative Considered**: Separate auth-proxy service
- ❌ Auth-proxy's public endpoint also requires OAuth
- ❌ Adds unnecessary complexity and latency

### SPCS Session Tokens

SPCS automatically provides session tokens at `/snowflake/session/token` for services to authenticate with Snowflake. This eliminates the need for:
- Managing service account credentials
- Key-pair JWT authentication
- Secret storage and rotation

## Deployment

### Dashboard
```bash
cd ui/dashboard/release
export INVOICEIQ_SNOW_CONNECT="invoiceiq"
./build_and_deploy.sh
```

### Backend
```bash
cd backend/release
export INVOICEIQ_SNOW_CONNECT="invoiceiq"
./build_and_deploy.sh
```

## Environment Variables

### Dashboard (`service_spec.yml`)
```yaml
env:
  BACKEND_URL: http://backend.ivzu.svc.spcs.internal:8001
```

### Backend (`service_spec.yml`)
```yaml
env:
  SNOWFLAKE_WAREHOUSE: compute_wh
  SNOWFLAKE_ROLE: invoiceiq_admin
```

## Service URLs

- **Dashboard**: https://m737yt-sfengineering-aifde.snowflakecomputing.app
- **Backend (internal)**: http://backend.ivzu.svc.spcs.internal:8001
- **Collector**: https://e437yt-sfengineering-aifde.snowflakecomputing.app

## Development

### Local Development
When running locally, services fall back to environment variables:
- Backend uses JWT key-pair authentication
- Dashboard can point to localhost backend

### SPCS Development
Services automatically detect SPCS environment:
- Check for `/snowflake/session/token` file
- Use OAuth session token if present
- Use internal DNS for service-to-service communication

## Troubleshooting

### Dashboard Shows "Failed to fetch"
1. Check backend is running: `snow spcs service status backend -c invoiceiq`
2. Check backend logs: `snow spcs service logs backend -c invoiceiq --container-name backend --instance-id 0`
3. Verify internal DNS: Backend should be accessible at `backend.ivzu.svc.spcs.internal:8001`

### Backend Can't Connect to Snowflake
1. Verify session token exists: Check logs for "Using SPCS OAuth session token"
2. Check role permissions: Ensure `invoiceiq_admin` role has necessary grants
3. Verify warehouse is running: `COMPUTE_WH` must be available

### Dashboard Returns 503
- Backend is likely having issues connecting to Snowflake
- Check backend logs for detailed error messages
- Common issues: Missing role, warehouse suspended, invalid token

## Security Considerations

1. **Internal Communication**: All backend API calls happen within SPCS network, never exposed to internet
2. **OAuth**: Users must authenticate with Snowflake to access dashboard
3. **Session Tokens**: Automatically managed by SPCS, no manual secret rotation
4. **CORS**: Configured to accept all origins (can be restricted for production)

## Future Enhancements

- [ ] User-level authentication for audit logging
- [ ] Role-based access control (RBAC)
- [ ] Rate limiting on public endpoints
- [ ] Metrics and monitoring integration
- [ ] Automated testing pipeline

