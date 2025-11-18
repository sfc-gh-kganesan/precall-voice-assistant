-- Example Job Service - Rust-based SPCS Job
-- This demonstrates a run-to-completion job with rate limiting and secrets

DROP SERVICE IF EXISTS <% SPCS_DATABASE_NAME %>.<% SPCS_SCHEMA_NAME %>.example_job_service;

-- Optional: Create secret for API key if needed
-- Uncomment and configure before deploying:
-- CREATE OR REPLACE SECRET <% SPCS_DATABASE_NAME %>.<% SPCS_SCHEMA_NAME %>.api_key_secret
--   TYPE = GENERIC_STRING
--   SECRET_STRING = 'your-api-key-here';

CREATE SERVICE <% SPCS_DATABASE_NAME %>.<% SPCS_SCHEMA_NAME %>.example_job_service
IN COMPUTE POOL <% SPCS_COMPUTE_POOL_NAME %>
FROM SPECIFICATION $$
spec:
  containers:
  - name: example-job-container
    image: <% SPCS_REPO_URL %>/example-job:latest
    env:
      # Uncomment to use secrets:
      # API_KEY:
      #   secretKeyRef:
      #     key: api_key_secret
      
      # For demo purposes, use a dummy API key (public APIs don't validate this)
      API_KEY: "demo-key-12345"
      
      # API endpoint to call
      API_ENDPOINT: "https://api.publicapis.org/entries"
      
      # Number of API requests to make
      NUM_REQUESTS: "10"
      
      # Rate limit (requests per second)
      RATE_LIMIT: "2"
      
      # Snowflake stage to upload results (optional)
      # STAGE_PATH: "@api_results_stage"
    
    resources:
      requests:
        memory: 512Mi
        cpu: 0.5
      limits:
        memory: 1Gi
        cpu: 1.0
    

  # Platform monitoring for observability
  platformMonitor:
    metricConfig:
      groups:
      - system
      - system_limits
$$
MIN_INSTANCES = 1
MAX_INSTANCES = 1
QUERY_WAREHOUSE = <% SPCS_WAREHOUSE_NAME %>
EXTERNAL_ACCESS_INTEGRATIONS = (<% SPCS_EAI_NAME %>);

