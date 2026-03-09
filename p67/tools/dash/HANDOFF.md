# P67 Dashboard - SPCS Deployment Handoff

## Overview

The P67 Dashboard is a React-based UI for managing P67 workflows, runs, logs, and interrupts. It has been deployed in two ways:
1. **Standalone SPCS Service** - Direct service deployment ✅ RECOMMENDED
2. **Native App** - Snowflake Native App with application package ⚠️ LIMITED (see Known Limitations)

**Standalone Service Endpoint:** `https://fzb46h6e-sfengineering-aifde.snowflakecomputing.app`
**Native App Endpoint:** `https://b3b46h6e-sfengineering-aifde.snowflakecomputing.app` (302/CSP errors)

### Known Limitations (Native App)
The Native App can display the UI but **API calls fail with 302/CSP errors** because:
- SPCS internal DNS is scoped per-application (cannot resolve `controld.ghw6if.svc.spcs.internal`)
- The public controld endpoint requires OAuth authentication which the proxy cannot provide
- SPCS ingress strips Authorization headers before forwarding to containers
- Browser Content-Security-Policy blocks cross-origin OAuth redirects (302)
- Result: API calls get 302 redirects that are blocked by CSP

**Use the Standalone Service** until one of these solutions is implemented:
1. Deploy controld as part of the same native app (RECOMMENDED - requires P67 architecture change)
2. Add service reference support for cross-app communication
3. Have controld expose an authenticated endpoint that accepts `sf-context-current-user` header without OAuth

## SECURITY CONCERNS

### External Access Integration (EAI) for Controld
**WARNING:** The native app deployment creates an EAI (`dash_controld_eai`) that allows egress to the P67 controld public endpoint.

**Potential Security Issues:**
1. **Network Exposure**: The EAI allows the native app to reach `frb46h6e-sfengineering-aifde.snowflakecomputing.app:443`
2. **OAuth Bypass Attempt**: The proxy attempts to forward auth headers, but this doesn't work due to SPCS ingress stripping
3. **Cross-Account Deployment**: If deployed to another account, it would attempt to reach this specific endpoint (security boundary)

**Can altering P67 controld service cause issues?**
- **YES** - Changes to P67's controld service configuration could affect:
  - Internal DNS names (breaking standalone service)
  - Public endpoint URL (breaking native app EAI rules)
  - Authentication requirements
  - API contract changes
- **Recommendation**: Coordinate P67 controld changes with dashboard team

### Hardcoded URLs Audit

| Location | URL/Value | Type | Dynamic Possible? |
|----------|-----------|------|-------------------|
| `deploy.sh` | `sfengineering-aifde` | Account name | ✅ Could use `snow connection` |
| `deploy.sh` | `controld.ghw6if.svc.spcs.internal:80` | Internal DNS | ⚠️ Hardcoded, specific to P67 account |
| `deploy-native-app.sh` | `frb46h6e-sfengineering-aifde.snowflakecomputing.app` | Public endpoint | ⚠️ Hardcoded, specific to P67 account |
| `native-app/setup.sql` | `frb46h6e-sfengineering-aifde.snowflakecomputing.app:443` | Network rule | ⚠️ Hardcoded |
| `native-app/dashboard_service_spec.yml` | `P67_API_URL` env var | API endpoint | ✅ Could be passed at runtime |
| `server/server.js` | Default fallback URL | API endpoint | ✅ Reads from env var |

### Dynamic Discovery Plan (NOT YET IMPLEMENTED)

**Goal**: Allow native app to auto-detect P67 controld on any account.

**Approach 1: Service Discovery via SHOW ENDPOINTS**
```sql
-- At app install/start time, query for P67 controld
SHOW ENDPOINTS IN SERVICE P67.APP.CONTROLD;
-- Parse the ingress_url and configure P67_API_URL env var
```
**Problem**: Requires cross-database access and assumes P67 app exists in same account.

**Approach 2: Consumer-Provided Configuration**
```sql
-- Add configuration procedure to native app
CREATE OR REPLACE PROCEDURE v1.configure_backend(p67_endpoint VARCHAR)
RETURNS VARCHAR
AS $$
  -- Update environment variable or config table
  -- Recreate service with new P67_API_URL
$$;
```
**Problem**: Still requires EAI approval for any endpoint.

**Approach 3: Reference-Based Discovery (FUTURE)**
```sql
-- Use Snowflake service references (if supported)
CREATE OR REPLACE SERVICE v1.dashboard_service
  ...
  SERVICE_REFERENCES = (controld_ref)
  ...
```
**Problem**: Cross-app service references not currently supported.

**Approach 4: Deploy Dashboard Inside P67 (RECOMMENDED)**
- Add dashboard as a service in P67's native app
- Use internal DNS which is scoped to the same app
- No EAI needed, no OAuth issues
- **This is the correct architectural solution**

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Snowflake Account (SFENGINEERING-AIFDE)                │
│                                                                             │
│  ┌─────────────────────┐      ┌───────────────────────────────────────────┐│
│  │  STANDALONE SERVICE │      │  NATIVE APP                               ││
│  │  (P67_SRC.DASH)     │      │  (P67_DASH_APP)                           ││
│  │  ─────────────────  │      │  ─────────────────────────────────────────││
│  │  P67_DASH Service   │      │  Dashboard Service                        ││
│  │  Uses internal DNS  │      │  Uses PUBLIC endpoint (requires EAI)      ││
│  │  to reach controld  │      │  to reach controld - FAILS WITH 302/CSP   ││
│  │  ✅ WORKS           │      │  ⚠️ AUTH FAILS                            ││
│  └─────────┬───────────┘      └───────────────┬───────────────────────────┘│
│            │                                   │                            │
│            │ Internal DNS                      │ HTTPS (OAuth Required)     │
│            ▼                                   ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  P67.APP.CONTROLD Service                                               ││
│  │  Internal: controld.ghw6if.svc.spcs.internal:80 (only same-app)         ││
│  │  Public:   frb46h6e-sfengineering-aifde.snowflakecomputing.app          ││
│  │            ↑ Requires Snowflake OAuth (returns 302 if not authed)       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| React Frontend | `src/` | UI built with Vite, React, Stellar components |
| Express Server | `server/server.js` | Serves static files + proxies `/api/*` to controld |
| Docker Image | `Dockerfile` | Packages Express server + built frontend |
| Deploy Script (Standalone) | `deploy.sh` | Automates build and deployment to SPCS |
| Deploy Script (Native App) | `deploy-native-app.sh` | Automates native app versioning/patching |
| Native App Files | `native-app/` | manifest.yml, setup.sql, dashboard_service_spec.yml |

### Service Communication

**Standalone Service (WORKS):**
- Uses internal SPCS DNS: `http://controld.ghw6if.svc.spcs.internal:80`
- Same-app internal DNS resolution works

**Native App (302/CSP ERROR):**
- Uses public endpoint with External Access Integration: `https://frb46h6e-sfengineering-aifde.snowflakecomputing.app`
- OAuth redirect blocked by CSP
- Requires app specification approval for external access

**Both:**
- Browser → Dashboard: Public endpoint via SPCS ingress (requires Snowflake auth)
- User Identity: SPCS injects `sf-context-current-user` header automatically

## Key Files

### Frontend
- `src/api/client.ts` - API client, all calls go to `/api/*`
- `src/index.css` - CSS variables including dark mode support
- `src/components/BaltoThemeWrapper.tsx` - Detects OS color scheme for dark mode
- `src/pages/InterruptsPage.tsx` - Interrupt management UI

### Backend/Deployment
- `server/server.js` - Express server with proxy middleware
- `Dockerfile` - Container definition for SPCS
- `deploy.sh` - Standalone SPCS deployment script
- `deploy-native-app.sh` - Native app deployment script

### Snowflake Objects

**Standalone Service:**
- **Database:** `P67_SRC`
- **Schema:** `DASH`
- **Service:** `P67_DASH`
- **Image Repository:** `P67_SRC.DASH.IMG_REPO`
- **Compute Pool:** `SANDBOX_COMPUTE_POOL_CPU`

**Native App:**
- **Application Package:** `P67_DASH_PKG`
- **Application:** `P67_DASH_APP`
- **Release Channel:** `QA` (Version V3)
- **Stage:** `P67_SRC.DASH.NATIVE_APP_STAGE`
- **Network Rule:** `v1.controld_egress_rule` (in app schema)
- **External Access Integration:** `dash_controld_eai` (in app schema)
- **App Specification:** `CONTROLD_ACCESS_SPEC` (approved)

## Deployment

### Quick Deploy (Standalone - RECOMMENDED)
```bash
cd /Users/vb/src/github.com/snowflake-eng/aura/p67/tools/dash
./deploy.sh
```

### Quick Deploy (Native App - HAS KNOWN ISSUES)
```bash
cd /Users/vb/src/github.com/snowflake-eng/aura/p67/tools/dash
./deploy-native-app.sh [--patch] [--channel QA]
```

Options:
- `--skip-build`: Skip Docker build (use existing local image)
- `--skip-frontend`: Skip frontend rebuild (use existing dist/)
- `--patch`: Create patch instead of new version
- `--channel NAME`: Release channel (default: QA)

### Manual Steps (if script fails)

1. **Build frontend:**
   ```bash
   pnpm run build
   ```

2. **Build Docker image (MUST use linux/amd64):**
   ```bash
   docker build --platform linux/amd64 -t p67-dash:latest .
   ```

3. **Login to Snowflake registry (if needed):**
   ```bash
   snow spcs image-registry login
   # OR
   docker login sfengineering-aifde.registry.snowflakecomputing.com
   ```

4. **Tag and push:**
   ```bash
   VERSION="v$(date +%s)"
   docker tag p67-dash:latest sfengineering-aifde.registry.snowflakecomputing.com/p67_src/dash/img_repo/p67-dash:${VERSION}
   docker push sfengineering-aifde.registry.snowflakecomputing.com/p67_src/dash/img_repo/p67-dash:${VERSION}
   ```

5. **Update service:**
   ```sql
   ALTER SERVICE P67_SRC.DASH.P67_DASH FROM SPECIFICATION $$
   spec:
     containers:
       - name: dashboard
         image: /p67_src/dash/img_repo/p67-dash:${VERSION}
         env:
           P67_API_URL: "http://controld.ghw6if.svc.spcs.internal:80"
           PORT: "3001"
         resources:
           requests:
             memory: 256M
             cpu: 0.5
           limits:
             memory: 512M
             cpu: 1
         readinessProbe:
           path: /health
           port: 3001
     endpoints:
       - name: dashboard
         port: 3001
         public: true
   $$;
   ```

## Native App Deployment (Manual)

### Deploy New Version to Native App

1. **Build and push image (same as standalone):**
   ```bash
   VERSION="v$(date +%s)"
   npm run build
   docker build --platform linux/amd64 -t p67-dash:${VERSION} .
   docker tag p67-dash:${VERSION} sfengineering-aifde.registry.snowflakecomputing.com/p67_src/dash/img_repo/p67-dash:${VERSION}
   docker push sfengineering-aifde.registry.snowflakecomputing.com/p67_src/dash/img_repo/p67-dash:${VERSION}
   ```

2. **Update native-app files with new version:**
   - Edit `native-app/dashboard_service_spec.yml` - update image tag
   - Edit `native-app/manifest.yml` - update image tag

3. **Upload files to stage:**
   ```bash
   snow sql -q "PUT file://native-app/manifest.yml @P67_SRC.DASH.NATIVE_APP_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
   snow sql -q "PUT file://native-app/setup.sql @P67_SRC.DASH.NATIVE_APP_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
   snow sql -q "PUT file://native-app/dashboard_service_spec.yml @P67_SRC.DASH.NATIVE_APP_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
   ```

4. **Add patch to version:**
   ```sql
   ALTER APPLICATION PACKAGE P67_DASH_PKG 
   ADD PATCH FOR VERSION V3 USING '@P67_SRC.DASH.NATIVE_APP_STAGE/';
   ```

5. **Upgrade the application:**
   ```sql
   ALTER APPLICATION P67_DASH_APP UPGRADE;
   ```

### Native App Commands

```sql
-- Check status
CALL P67_DASH_APP.V1.DASHBOARD_STATUS();

-- View logs
CALL P67_DASH_APP.V1.DASHBOARD_LOGS();

-- Get URL
CALL P67_DASH_APP.V1.DASHBOARD_URL();

-- Stop service
CALL P67_DASH_APP.APP.STOP_DASHBOARD();

-- Start service
CALL P67_DASH_APP.V1.START_DASHBOARD('SANDBOX_COMPUTE_POOL_CPU');

-- Check app specifications (for external access)
SHOW SPECIFICATIONS IN APPLICATION P67_DASH_APP;

-- Approve external access specification (if pending)
ALTER APPLICATION P67_DASH_APP APPROVE SPECIFICATION CONTROLD_ACCESS_SPEC SEQUENCE_NUMBER = 1;
```

## Gotchas and Learnings

### 1. Docker Image Architecture
**Problem:** SPCS only runs `linux/amd64` images. Building on Apple Silicon without `--platform` flag creates `arm64` images that fail silently.

**Solution:** Always build with:
```bash
docker build --platform linux/amd64 -t p67-dash:latest .
```

### 2. Express Path Wildcard Syntax
**Problem:** Express 5.x / newer path-to-regexp doesn't support `app.get("*")`.

**Error:** `PathError [TypeError]: Missing parameter name at index 1: *`

**Solution:** Use named splat parameter:
```javascript
app.get("/{*splat}", (req, res) => { ... });
```

### 3. http-proxy-middleware v3.x API Changes
**Problem:** v3.x changed the configuration API from `onProxyReq` to `on: { proxyReq: ... }`.

**Solution:**
```javascript
const apiProxy = createProxyMiddleware({
  target: P67_API_URL,
  changeOrigin: true,
  on: {
    proxyReq: (proxyReq, req) => { ... },
    proxyRes: (proxyRes, req) => { ... },
    error: (err, req, res) => { ... }
  }
});
```

### 4. Express Mount Path Stripping
**Problem:** When using `app.use("/api", proxy)`, Express strips `/api` from the URL before passing to middleware. So `/api/workflow/list` becomes `/workflow/list`.

**Solution:** Use `pathRewrite` to add prefix back:
```javascript
createProxyMiddleware({
  target: P67_API_URL,
  pathRewrite: (path) => "/api" + path,
  // ...
});
```

### 5. Controld Requires User Header
**Problem:** Controld returns 500 if `sf-context-current-user` header is missing.

**Solution:** SPCS ingress automatically injects this header for authenticated requests. The proxy must forward it:
```javascript
on: {
  proxyReq: (proxyReq, req) => {
    const sfUser = req.headers["sf-context-current-user"];
    if (sfUser) {
      proxyReq.setHeader("sf-context-current-user", sfUser);
    }
  }
}
```

### 6. Compute Pool Exclusivity
**Problem:** `SERVICE_COMPUTE_POOL` is exclusive to the P67 native app.

**Solution:** Use `SANDBOX_COMPUTE_POOL_CPU` for standalone services.

### 7. SPCS Probe Configuration
**Problem:** Advanced probe options like `initialDelaySeconds` aren't recognized.

**Solution:** Use simple probe config:
```yaml
readinessProbe:
  path: /health
  port: 3001
```

### 8. Image Caching
**Problem:** SPCS may cache images by tag. Using `latest` tag doesn't always pull new images.

**Solution:** Use unique version tags (timestamps):
```bash
VERSION="v$(date +%s)"
```

### 9. Native App External Access (EAI)
**Problem:** Native App services cannot reach external endpoints (including other SPCS public endpoints) without External Access Integration.

**Solution:** 
1. Add `CREATE EXTERNAL ACCESS INTEGRATION` privilege to manifest.yml
2. Create network rule and EAI in setup.sql
3. Create app specification for consumer approval
4. Use EAI when creating service with `EXTERNAL_ACCESS_INTEGRATIONS`
5. Consumer must approve the app specification

### 10. Native App Internal DNS Scoping (ROOT CAUSE OF 302 ERROR)
**Problem:** SPCS internal DNS (e.g., `controld.ghw6if.svc.spcs.internal`) is scoped per application. Native app cannot resolve DNS for services in other apps/databases.

**Why 302 Occurs:**
1. Native app must use public endpoint (internal DNS doesn't work)
2. Public endpoint requires Snowflake OAuth
3. SPCS ingress strips Authorization header before forwarding to container
4. Container makes unauthenticated request to public endpoint
5. Public endpoint returns 302 redirect to OAuth flow
6. Browser blocks redirect due to CSP (cross-origin)

**Solution:** The only real fix is to deploy dashboard inside the P67 native app so it can use internal DNS.

### 11. Release Channel Version Limits
**Problem:** Release channels have a limit of 2 versions. Adding a new version fails if 2 exist.

**Solution:** Drop old version first:
```sql
ALTER APPLICATION PACKAGE P67_DASH_PKG MODIFY RELEASE CHANNEL ALPHA DROP VERSION V1;
```

### 12. Native App Compute Pool Grants
**Problem:** Native apps don't automatically have access to compute pools.

**Solution:** Grant usage on compute pool to the application:
```sql
GRANT USAGE ON COMPUTE POOL SANDBOX_COMPUTE_POOL_CPU TO APPLICATION P67_DASH_APP;
```

### 13. pathRewrite with originalUrl
**Problem:** When using Express mount paths with http-proxy-middleware, the path variable in pathRewrite is already modified.

**Solution:** Use `req.originalUrl` to get the full original path:
```javascript
pathRewrite: (pathStr, req) => req.originalUrl
```

### 14. Docker Registry Auth Expiration
**Problem:** Registry authentication expires during long build/push operations.

**Error:** `unauthorized: Authorization Failure`

**Solution:** Re-login before push:
```bash
snow spcs image-registry login
docker push ...
```

### 15. CSP Blocking OAuth Redirects
**Problem:** When proxy returns 302 from public endpoint, browser CSP blocks the cross-origin redirect.

**Why:** SPCS sets strict CSP headers that prevent redirects to other origins.

**Solution:** Cannot be fixed at proxy level - need to use internal DNS (requires same-app deployment).

## Useful Commands

### Check Service Status
```sql
SELECT SYSTEM$GET_SERVICE_STATUS('P67_SRC.DASH.P67_DASH');
```

### View Service Logs
```sql
CALL SYSTEM$GET_SERVICE_LOGS('P67_SRC.DASH.P67_DASH', '0', 'dashboard', 500);
```

### Show Endpoints
```sql
SHOW ENDPOINTS IN SERVICE P67_SRC.DASH.P67_DASH;
```

### Suspend/Resume Service
```sql
ALTER SERVICE P67_SRC.DASH.P67_DASH SUSPEND;
ALTER SERVICE P67_SRC.DASH.P67_DASH RESUME;
```

### View Controld Service (for reference)
```sql
DESCRIBE SERVICE P67.APP.CONTROLD;
SHOW ENDPOINTS IN SERVICE P67.APP.CONTROLD;
```

### Check Native App External Access
```sql
SHOW SPECIFICATIONS IN APPLICATION P67_DASH_APP;
SELECT SYSTEM$GET_SERVICE_STATUS('P67_DASH_APP.V1.DASHBOARD_SERVICE');
```

## Local Development

```bash
cd /Users/vb/src/github.com/snowflake-eng/aura/p67/tools/dash

# Install dependencies
pnpm install

# Start dev server (proxies to local controld on port 3002)
pnpm run dev

# Or specify custom API URL
P67_API_URL=http://localhost:3002 pnpm run dev
```

## Dark Mode

The UI supports OS-level dark mode via:
1. CSS custom properties in `src/index.css` with `@media (prefers-color-scheme: dark)`
2. `BaltoThemeWrapper.tsx` detects system preference and sets Stellar `colorScheme`

To test dark mode, change your OS/browser appearance settings.

## API Endpoints (via controld)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflow/list` | GET | List all workflows |
| `/api/workflow/:id/manifest` | GET | Get workflow manifest |
| `/api/workflow/:id/run` | POST | Run a workflow |
| `/api/workflow/:id` | DELETE | Delete a workflow |
| `/api/workflow/interrupts` | GET | List interrupts |
| `/api/workflow/interrupts/:id` | GET | Get interrupt details |
| `/api/workflow/interrupts/:id/resume` | POST | Resume an interrupt |
| `/api/log/runs` | GET | List runs for a workflow |
| `/api/log/list` | GET | List logs for a run |
| `/api/whoami` | GET | Get current user info |

## Troubleshooting

### 302/CSP Errors in Native App
**Cause:** Native app proxy cannot authenticate to controld's public endpoint.
**Solution:** Use standalone service (`deploy.sh`) until dashboard is integrated into P67 native app.

### Service stuck in PENDING
1. Check logs: `CALL SYSTEM$GET_SERVICE_LOGS(...)`
2. Common causes: bad image, failed health check, resource limits

### 404 on API calls
1. Check proxy logs for path issues
2. Verify controld is running: `SELECT SYSTEM$GET_SERVICE_STATUS('P67.APP.CONTROLD')`
3. Check internal DNS resolution in logs

### 500 errors from controld
1. Usually missing `sf-context-current-user` header
2. Check proxy is forwarding headers correctly

### Image push fails
1. Re-login to registry: `snow spcs image-registry login`
2. Verify image repo exists: `SHOW IMAGE REPOSITORIES IN SCHEMA P67_SRC.DASH`

## Future Improvements

1. **CRITICAL**: Move dashboard service into P67 native app to use internal DNS
2. Add CI/CD pipeline for automated deployments
3. Add health check that verifies controld connectivity
4. Consider using Snowflake secrets for sensitive config
5. Add request logging/metrics
6. Consider blue-green deployments for zero-downtime updates
7. Implement dynamic endpoint discovery (see Dynamic Discovery Plan above)
