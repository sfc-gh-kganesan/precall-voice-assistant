# Dashboard Cleanup Plan

## Status
Dashboard has been integrated into the P67 native app. The old standalone deployment at `tools/dash/` is still functional but should be deprecated.

## Current State (as of March 2026)

| Component | Location | Status |
|-----------|----------|--------|
| Dashboard code | `p67/tools/dash/` | Active - still used for builds |
| Dashboard image | `p67_src/dash/img_repo/p67-dash` | Active |
| Native app spec | `p67/native-app/dashboard_service_spec.yml` | Active |
| Standalone SPCS | `P67_SRC.DASH.P67_DASH` | Active - fallback option |
| Old separate native app | `P67_DASH_APP` / `P67_DASH_PKG` | Deprecated |

## Working Endpoints

- **Integrated (P67 Native App)**: https://f3b46h6e-sfengineering-aifde.snowflakecomputing.app
- **Standalone SPCS**: https://fzb46h6e-sfengineering-aifde.snowflakecomputing.app

Both work - integrated uses internal DNS, standalone uses internal DNS too.

## Cleanup Tasks

### Phase 1: Move Dashboard Code (Priority: Medium)
Move dashboard source code to follow project conventions.

1. Create `p67/containers/dashboard/` directory
2. Move these from `tools/dash/`:
   - `Dockerfile`
   - `server/server.js`
   - `package.json` (server deps only)
3. Keep `tools/dash/src/` for React source OR move to `packages/dashboard/`
4. Update build scripts to use new location
5. Consider moving image to `p67_src/core/img_repo/p67-dash` (consolidated)

### Phase 2: Consolidate Build System (Priority: Medium)
Unify the build and deployment process.

1. Add dashboard build to root `Makefile` or existing build scripts
2. Create unified deploy script for native app (similar to controld workflow)
3. Keep `tools/dash/deploy.sh` for local development only
4. Remove `tools/dash/deploy-native-app.sh` (deprecated)

### Phase 3: Deprecate Old Artifacts (Priority: Low)
Remove legacy deployment artifacts once integrated version is validated.

```sql
-- Drop standalone SPCS service (after validation period)
DROP SERVICE P67_SRC.DASH.P67_DASH;

-- Drop old separate native app
DROP APPLICATION P67_DASH_APP;
DROP APPLICATION PACKAGE P67_DASH_PKG;
```

Remove from filesystem:
- `tools/dash/native-app/` directory (old separate native app files)

### Phase 4: Update Documentation (Priority: Low)
Update all documentation to reflect new architecture.

1. Update main P67 README with dashboard info
2. Archive or remove `tools/dash/HANDOFF.md` (references old architecture)
3. Update `native-app/README.md` to document both services
4. Document dashboard procedures: `V1.START_DASHBOARD()`, `V1.DASHBOARD_URL()`

## Key Learnings

### Internal DNS Format
SPCS internal DNS uses format: `<service_name>.<compute_pool_id>.svc.spcs.internal`

For controld in P67: `controld.ghw6if.svc.spcs.internal:80`

This is NOT `app.controld` or `<schema>.<service>` format.

### Image Repository Access
Native app packages need explicit grants to read from image repositories:
```sql
GRANT READ ON IMAGE REPOSITORY P67_SRC.DASH.IMG_REPO TO ROLE P67_PROVIDER_ADMIN_RL;
```

### Multiple Services in One Native App
A native app can have:
- Multiple Docker images in `manifest.yml` `container_services.images`
- Multiple SPCS services created via `CREATE SERVICE` in setup.sql
- Each service can use different compute pools

## Rollback Instructions

If issues arise with integrated dashboard:

1. Use standalone SPCS service: https://fzb46h6e-sfengineering-aifde.snowflakecomputing.app
2. Or redeploy standalone:
   ```bash
   cd p67/tools/dash && ./deploy.sh
   ```
3. To remove integrated dashboard from native app:
   ```sql
   DROP SERVICE P67.APP.DASHBOARD;
   ```
   Then revert changes to `manifest.yml`, `setup.sql`, remove `dashboard_service_spec.yml`

## Notes

- The dashboard uses the same Docker image for both deployments
- Only difference is `P67_API_URL` env var (both now use internal DNS)
- Keep standalone option available until integrated version is validated in production
- The `ghw6if` in the DNS name is the compute pool identifier - may change if pool is recreated
