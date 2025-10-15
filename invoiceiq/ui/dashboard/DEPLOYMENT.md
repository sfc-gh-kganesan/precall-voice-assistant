# Dashboard Deployment Guide

## Architecture

The dashboard uses an **Express proxy server** integrated into the frontend container to communicate with the backend via internal SPCS networking.

```
User Browser → Dashboard Container (Express)
                    ↓ (internal SPCS network)
              Backend Container
```

## How It Works

1. **Express Server** (`server.js`) serves the React frontend and proxies API calls
2. **Internal Networking**: All `/api/*` requests are forwarded to `backend.ivzu.svc.spcs.internal:8001`
3. **No Authentication**: Internal SPCS communication doesn't require OAuth tokens

## Deployment

### Build and Deploy

```bash
cd ui/dashboard/release
export INVOICEIQ_SNOW_CONNECT="invoiceiq"
./build_and_deploy.sh
```

The script will:
1. Build the Docker image with Express proxy server
2. Push to Snowflake image repository
3. Upgrade the dashboard service

### Get Dashboard URL

```bash
cd ui/dashboard/scripts
export INVOICEIQ_SNOW_CONNECT="invoiceiq"
./get_spcs_endpoint.sh
```

## Configuration

The dashboard is configured via `service_spec.yml`:

```yaml
env:
  BACKEND_URL: http://backend.ivzu.svc.spcs.internal:8001
```

This tells the Express proxy where to forward API requests.

## Testing

1. Open the dashboard URL in your browser
2. Check browser DevTools Network tab
3. API calls should go to `/api/*` (proxied internally)

## Troubleshooting

### "Failed to fetch" Errors

**Check backend status:**
```bash
snow spcs service status backend -c invoiceiq
```

**Check backend logs:**
```bash
snow spcs service logs backend -c invoiceiq --container-name backend --instance-id 0
```

**Check dashboard proxy logs:**
```bash
snow spcs service logs dashboard -c invoiceiq --container-name dashboard --instance-id 0
```

### Backend Returns 503

Backend likely can't connect to Snowflake:
- Verify session token: Check logs for "Using SPCS OAuth session token"
- Check role: Ensure `invoiceiq_admin` has necessary permissions
- Verify warehouse: `COMPUTE_WH` must be running

## Local Development

For local development:

```bash
cd ui/dashboard
export BACKEND_URL="http://localhost:8001"
npm install
npm run dev
```

The proxy server will use the `BACKEND_URL` environment variable.

