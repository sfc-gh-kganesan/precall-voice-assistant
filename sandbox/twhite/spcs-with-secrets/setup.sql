-- =============================================================================
-- Snowflake Container Services (SPCS) Setup with Secrets and Network Rules
-- Demo: Job Service with Rust API Client
-- =============================================================================

-- Set your context
-- USE ROLE ACCOUNTADMIN; -- Uncomment and adjust role as needed
-- USE WAREHOUSE COMPUTE_WH; -- Uncomment and adjust warehouse as needed

-- =============================================================================
-- 1. Create Database and Schema
-- =============================================================================
CREATE DATABASE IF NOT EXISTS SPCS_DEMO;
USE DATABASE SPCS_DEMO;

CREATE SCHEMA IF NOT EXISTS API_JOBS;
USE SCHEMA API_JOBS;

-- =============================================================================
-- 2. Create Image Repository
-- =============================================================================
CREATE OR REPLACE IMAGE REPOSITORY spcs_demo_repo;

-- Show the repository URL - you'll need this for docker push
SHOW IMAGE REPOSITORIES;

-- =============================================================================
-- 2b. Create Internal Stage for File Persistence
-- =============================================================================
-- Stage for storing API results and job outputs
CREATE OR REPLACE STAGE api_results_stage
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Stage for storing API execution results from container services';

-- Show stage information
SHOW STAGES;
DESC STAGE api_results_stage;

-- =============================================================================
-- 3. Create Network Rule for External API Access
-- =============================================================================
-- This allows outbound access to the public API
-- Following best practices from: https://docs.snowflake.com/en/user-guide/api-authentication

CREATE OR REPLACE NETWORK RULE allow_public_api
  TYPE = HOST_PORT
  MODE = EGRESS
  VALUE_LIST = (
    'api.publicapis.org:443',
    'httpbin.org:443',
    'jsonplaceholder.typicode.com:443'
  )
  COMMENT = 'Allow access to public APIs for demo purposes';

-- =============================================================================
-- 4. Create External Access Integration
-- =============================================================================
-- Links the network rule to allow external access
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION api_access_integration
  ALLOWED_NETWORK_RULES = (allow_public_api)
  ENABLED = TRUE
  COMMENT = 'Integration for external API access with network rules';

-- =============================================================================
-- 5. Create Secrets
-- =============================================================================
-- Demo secret using GENERIC_STRING type for API key
-- In production, use appropriate secret type based on your auth method

CREATE OR REPLACE SECRET api_key_secret
  TYPE = GENERIC_STRING
  SECRET_STRING = 'demo-api-key-12345-for-testing'
  COMMENT = 'API key for external service authentication';

-- Optional: Create a basic auth secret (username/password)
CREATE OR REPLACE SECRET basic_auth_secret
  TYPE = PASSWORD
  USERNAME = 'demo_user'
  PASSWORD = 'demo_password_123'
  COMMENT = 'Basic authentication credentials (demo)';

-- =============================================================================
-- 6. Create Compute Pool
-- =============================================================================
-- Compute pool provides resources for running containers
CREATE COMPUTE POOL IF NOT EXISTS job_pool
  MIN_NODES = 1
  MAX_NODES = 3
  INSTANCE_FAMILY = CPU_X64_XS
  AUTO_RESUME = TRUE
  AUTO_SUSPEND_SECS = 600
  COMMENT = 'Compute pool for API job services';

-- Check compute pool status
SHOW COMPUTE POOLS;
-- Wait for compute pool to be ACTIVE or IDLE before creating service

-- =============================================================================
-- 7. Create Service (after pushing Docker image)
-- =============================================================================
-- IMPORTANT: Run this AFTER you've built and pushed your Docker image
-- Uncomment and update the image path after pushing

/*
CREATE OR REPLACE SERVICE api_job_service
  IN COMPUTE POOL job_pool
  FROM SPECIFICATION $$
spec:
  containers:
  - name: api-client
    image: /spcs_demo/api_jobs/spcs_demo_repo/spcs-api-demo:latest
    env:
      API_KEY:
        secretKeyRef:
          key: api_key_secret
      API_ENDPOINT: "https://api.publicapis.org/entries"
      NUM_REQUESTS: "10"
      RATE_LIMIT: "2"
      STAGE_PATH: "@api_results_stage"
    volumeMounts:
    - name: output
      mountPath: /tmp/spcs_output
  volumes:
  - name: output
    source: "@api_results_stage"
  externalAccessIntegrations:
  - api_access_integration
$$
MIN_INSTANCES = 1
MAX_INSTANCES = 1
COMMENT = 'Job service for rate-limited API requests with file persistence';
*/

-- =============================================================================
-- 8. Monitor and Manage Service
-- =============================================================================

-- Check service status
SHOW SERVICES IN SCHEMA;

-- View service details
-- DESC SERVICE api_job_service;

-- Check service logs (after service is created)
-- CALL SYSTEM$GET_SERVICE_LOGS('api_job_service', 0, 'api-client');

-- Check service status
-- CALL SYSTEM$GET_SERVICE_STATUS('api_job_service');

-- =============================================================================
-- 9. Cleanup (Optional)
-- =============================================================================
/*
-- Drop service
DROP SERVICE IF EXISTS api_job_service;

-- Drop compute pool (must drop services first)
DROP COMPUTE POOL IF EXISTS job_pool;

-- Drop secrets
DROP SECRET IF EXISTS api_key_secret;
DROP SECRET IF EXISTS basic_auth_secret;

-- Drop integrations
DROP EXTERNAL ACCESS INTEGRATION IF EXISTS api_access_integration;
DROP NETWORK RULE IF EXISTS allow_public_api;

-- Drop stage
DROP STAGE IF EXISTS api_results_stage;

-- Drop image repository
DROP IMAGE REPOSITORY IF EXISTS spcs_demo_repo;

-- Drop schema and database
DROP SCHEMA IF EXISTS API_JOBS;
DROP DATABASE IF EXISTS SPCS_DEMO;
*/

-- =============================================================================
-- Verification Queries
-- =============================================================================

-- List all secrets
SHOW SECRETS;

-- List network rules
SHOW NETWORK RULES;

-- List external access integrations
SHOW EXTERNAL ACCESS INTEGRATIONS;

-- Describe a secret (shows metadata, not the actual secret value)
DESC SECRET api_key_secret;

-- List stages including our results stage
SHOW STAGES;

-- Verify stage can be listed
LIST @api_results_stage;

SELECT 'Setup complete! Next steps:' AS MESSAGE
UNION ALL
SELECT '1. Build Docker image: docker build -t spcs-api-demo .'
UNION ALL
SELECT '2. Tag image with repository URL'
UNION ALL
SELECT '3. Push image to Snowflake repository'
UNION ALL
SELECT '4. Create service using the CREATE SERVICE command above'
UNION ALL
SELECT '5. Monitor logs with SYSTEM$GET_SERVICE_LOGS'
UNION ALL
SELECT '6. View results files: LIST @api_results_stage';

