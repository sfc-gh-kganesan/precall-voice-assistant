-- Cleanup script for SPCS demo resources

USE DATABASE SPCS_DEMO;
USE SCHEMA API_JOBS;

-- Drop service first
DROP SERVICE IF EXISTS api_job_service;

-- Wait a moment for service to fully terminate
SELECT SYSTEM$WAIT(5);

-- Drop compute pool (requires services to be dropped first)
DROP COMPUTE POOL IF EXISTS job_pool;

-- Drop secrets
DROP SECRET IF EXISTS api_key_secret;
DROP SECRET IF EXISTS basic_auth_secret;

-- Drop integrations and rules
DROP EXTERNAL ACCESS INTEGRATION IF EXISTS api_access_integration;
DROP NETWORK RULE IF EXISTS allow_public_api;

-- Drop stage
DROP STAGE IF EXISTS api_results_stage;

-- Drop image repository
DROP IMAGE REPOSITORY IF EXISTS spcs_demo_repo;

-- Drop schema and database
DROP SCHEMA IF EXISTS API_JOBS;
DROP DATABASE IF EXISTS SPCS_DEMO;

SELECT 'Cleanup complete' AS status;

