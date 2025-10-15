# Add Docker and SPCS Deployment Support for InvoiceIQ Dashboard and Backend

## Summary

This PR adds full Snowpark Container Services (SPCS) deployment support for the InvoiceIQ dashboard (frontend) and backend API, enabling them to run as containerized services within Snowflake with seamless internal networking.

## Problem

The InvoiceIQ dashboard and backend were not deployable to SPCS, limiting the solution to local development only. Additionally, service-to-service communication in SPCS requires understanding of internal networking patterns to avoid OAuth complexity.

## Solution

### Key Architecture Changes

```
User Browser → Dashboard Container (Express + React)
                    ↓ (internal SPCS network, no auth required)
              Backend Container (FastAPI)
                    ↓ (OAuth session token)
              Snowflake Database
```

**Internal SPCS Networking**: Services communicate via internal DNS (`backend.ivzu.svc.spcs.internal`) without requiring OAuth tokens, while SPCS automatically provides session tokens for Snowflake database connections.

## Changes

### 1. Frontend Dashboard (`ui/dashboard/`)

**Docker Support:**
- ✅ **Dockerfile**: Multi-stage build with Node.js for React application
- ✅ **Express Proxy Server** (`server.js`): Integrated proxy that serves static React files and forwards `/api/*` requests to backend using internal SPCS DNS
- ✅ **API Service** (`api.ts`, `mapper.ts`): Complete API client for invoice operations with data transformation layer
- ✅ **.dockerignore**: Optimized build context

**SPCS Deployment:**
- ✅ **service_spec.yml**: SPCS service configuration with internal backend URL
- ✅ **Deployment Scripts**: 
  - `build_and_deploy.sh` - Build and push Docker image, upgrade service
  - `create_service.sh` - Initial service creation
  - `drop_service.sh` - Service cleanup
  - `get_spcs_endpoint.sh` - Retrieve public dashboard URL
  - `get_spcs_logs.sh` - View container logs

**Key Features:**
- Uses `/api` prefix for all backend calls (proxied internally)
- No OAuth tokens required in frontend code
- Automatic service discovery via SPCS internal DNS

### 2. Backend API (`backend/`)

**Docker Support:**
- ✅ **Dockerfile**: Python 3.11 with `uv` for fast dependency management
- ✅ **Multi-platform builds**: Supports both ARM64 (local dev) and AMD64 (SPCS)
- ✅ **uv.lock**: Locked dependencies for reproducible builds

**SPCS Authentication:**
- ✅ **Automatic environment detection**: Checks for `/snowflake/session/token` to determine if running in SPCS
- ✅ **OAuth session tokens**: Uses SPCS-provided tokens when in cloud environment
- ✅ **Local development fallback**: Falls back to JWT key-pair authentication for local development

```python
if os.path.isfile("/snowflake/session/token"):
    # SPCS environment - use OAuth session token
    config = {
        "authenticator": "oauth",
        "token": open("/snowflake/session/token").read(),
        ...
    }
else:
    # Local environment - use JWT key-pair
    config = {
        "authenticator": "SNOWFLAKE_JWT",
        "private_key_file": os.getenv("SNOWFLAKE_KEY"),
        ...
    }
```

**SPCS Deployment:**
- ✅ **service_spec.yml**: Service configuration with warehouse and role settings
- ✅ **Deployment Scripts**: Complete lifecycle management (build, deploy, create, drop, logs)
- ✅ **Health checks**: Readiness probe on `/health` endpoint

### 3. Documentation

**Added:**
- ✅ **backend/README.md**: Comprehensive backend documentation with API reference, deployment instructions, and architecture details
- ✅ **Updated root README.md**: Project-wide documentation with deployment guide

**Enhanced:**
- ✅ **ui/dashboard/README.md**: Added SPCS deployment section
- ✅ Clear deployment instructions for both local and cloud environments

## Technical Implementation

### Frontend Proxy Pattern

Instead of making direct API calls from the browser (which would require OAuth), the dashboard container includes an Express proxy server:

1. **Browser** → Makes requests to `/api/invoices`
2. **Express Proxy** → Forwards to `http://backend.ivzu.svc.spcs.internal:8001/invoices`
3. **Backend** → Responds with data
4. **Express Proxy** → Returns response to browser

This eliminates OAuth complexity while maintaining security through SPCS network isolation.

### Backend Authentication Strategy

The backend automatically adapts to its environment:
- **In SPCS**: Reads session token from `/snowflake/session/token` and uses OAuth
- **Locally**: Uses JWT key-pair authentication with private key file
- **Benefit**: Same codebase works in both environments without manual configuration

### Service Discovery

SPCS provides internal DNS for service-to-service communication:
- Services are accessible at `<service-name>.ivzu.svc.spcs.internal:<port>`
- No need for service discovery tools or configuration management
- Communication never leaves SPCS network

## Deployment

### Prerequisites
- Snowflake account with SPCS enabled
- Docker installed locally
- Snowflake CLI configured
- `INVOICEIQ_SNOW_CONNECT` environment variable set

### Deploy Backend
```bash
cd backend/release
export INVOICEIQ_SNOW_CONNECT="invoiceiq"
./build_and_deploy.sh
```

### Deploy Dashboard
```bash
cd ui/dashboard/release
export INVOICEIQ_SNOW_CONNECT="invoiceiq"
./build_and_deploy.sh
```

### Get Service URLs
```bash
# Dashboard
cd ui/dashboard/scripts && ./get_spcs_endpoint.sh

# Backend (internal only)
cd backend/scripts && ./get_spcs_endpoint.sh
```

## Testing

**Tested Scenarios:**
- ✅ Dashboard loads and displays invoice statistics
- ✅ Invoice list fetching (approved, pending, rejected)
- ✅ PDF viewing and downloading
- ✅ Bulk status updates
- ✅ Search and filtering
- ✅ Backend Snowflake connectivity via OAuth session tokens
- ✅ Internal SPCS networking between dashboard and backend
- ✅ Service restarts and upgrades

**Verified:**
- Express proxy correctly forwards requests to backend
- Backend successfully authenticates with Snowflake using session tokens
- All API endpoints return expected data
- No authentication errors in browser console

## Benefits

1. **Simplified Architecture**: No separate auth-proxy service needed
2. **No OAuth Complexity**: Internal networking eliminates token management in application code
3. **Automatic Authentication**: SPCS provides session tokens automatically
4. **Secure**: All service communication happens within SPCS network
5. **Environment Agnostic**: Same code works locally and in SPCS
6. **Fast Deployment**: Complete lifecycle scripts for all operations
7. **Production Ready**: Health checks, logging, and monitoring support

## Files Changed

- **23 files changed**: 1,807 insertions, 44 deletions
- **Core additions**: Docker support, SPCS configuration, deployment scripts, API services
- **No breaking changes**: Existing functionality preserved

## Future Enhancements

- [ ] Add rate limiting to Express proxy
- [ ] Implement request/response caching
- [ ] Add metrics and monitoring
- [ ] User-level authentication for audit trails
- [ ] Role-based access control (RBAC)

## Related Documentation

- See `ARCHITECTURE.md` for detailed system architecture (not in this PR, available locally)
- See `SOLUTION_FINAL.md` for solution summary (not in this PR, available locally)

