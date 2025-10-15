# InvoiceIQ Solution Summary

## Problem
Frontend deployed on SPCS couldn't communicate with backend due to Snowflake's OAuth requirements on all public endpoints.

## Solution
Use **internal SPCS networking** by integrating an Express proxy server into the frontend container.

## Architecture

```
User Browser → Dashboard (public, OAuth required)
                    ↓
              Express Proxy
                    ↓ (internal SPCS network, no auth!)
              Backend Container
                    ↓ (OAuth session token)
              Snowflake Database
```

## Key Implementation

### 1. Frontend Proxy Server
Added `server.js` to dashboard container:
```javascript
app.use('/api', createProxyMiddleware({
  target: 'http://backend.ivzu.svc.spcs.internal:8001',
  pathRewrite: { '^/api': '' }
}));
```

### 2. Backend Authentication
Uses SPCS-provided OAuth session token:
```python
if os.path.isfile("/snowflake/session/token"):
    config = {
        "authenticator": "oauth",
        "token": open("/snowflake/session/token").read(),
        ...
    }
```

### 3. Frontend API Calls
```typescript
const API_BASE_URL = '/api';  // Proxied by Express
const response = await fetch(`${API_BASE_URL}/invoices`);
```

## Why This Works

✅ **Browser → Dashboard**: OAuth handled by SPCS ingress (automatic)
✅ **Dashboard → Backend**: Internal SPCS networking (no auth needed)
✅ **Backend → Snowflake**: Session token provided by SPCS (automatic)

## Benefits

- No OAuth complexity in application code
- Fast internal communication
- Secure (never leaves SPCS network)
- Standard microservices pattern

## Services

- **Dashboard**: https://m737yt-sfengineering-aifde.snowflakecomputing.app
- **Backend (internal)**: http://backend.ivzu.svc.spcs.internal:8001

For detailed architecture and troubleshooting, see `ARCHITECTURE.md`.

