-- p67-dash SPCS Cross-Service Authentication Setup
-- Run these commands in Snowflake to configure access between p67-dash and p67

-- =============================================================================
-- STEP 1: Grant p67-dash service role access to p67 controld endpoints
-- =============================================================================

-- This grants the p67-dash Native App access to call p67 controld APIs
-- Run this after installing both p67 and p67-dash Native Apps

-- Option A: If p67-dash uses a service role
-- GRANT SERVICE ROLE P67.APP.CONTROLD!ALL_ENDPOINTS_USAGE 
--   TO APPLICATION P67_DASH;

-- Option B: Grant to a specific role that p67-dash will use
-- GRANT SERVICE ROLE P67.APP.CONTROLD!ALL_ENDPOINTS_USAGE 
--   TO ROLE <your_app_role>;

-- =============================================================================
-- STEP 2: Network configuration for internal DNS resolution
-- =============================================================================

-- p67-dash service can reach p67 controld via internal DNS:
-- controld.ghw6if.svc.spcs.internal:80
--
-- This is automatically available for services in the same Snowflake account.
-- No additional network rules are needed for same-account communication.

-- =============================================================================
-- STEP 3: Verify connectivity (run from p67-dash service)
-- =============================================================================

-- Test internal DNS resolution:
-- curl http://controld.ghw6if.svc.spcs.internal:80/api/health

-- =============================================================================
-- EXAMPLE: Full deployment sequence
-- =============================================================================

-- 1. Install p67 Native App (if not already installed)
-- CREATE APPLICATION p67 FROM APPLICATION PACKAGE p67_app_pkg;

-- 2. Install p67-dash Native App
-- CREATE APPLICATION p67_dash FROM APPLICATION PACKAGE p67_dash_app_pkg;

-- 3. Create compute pool for p67-dash
-- CALL p67_dash.app.create_compute_pool('P67_DASH_POOL', 'X-SMALL');

-- 4. Grant p67 service access to p67-dash
-- GRANT SERVICE ROLE P67.APP.CONTROLD!ALL_ENDPOINTS_USAGE 
--   TO APPLICATION p67_dash;

-- 5. Start the dashboard service
-- CALL p67_dash.app.start_dashboard_service(
--   'P67_DASH_POOL',
--   'controld.ghw6if.svc.spcs.internal:80'
-- );

-- 6. Get the dashboard URL
-- CALL p67_dash.app.get_dashboard_url();
