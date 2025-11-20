-- Initialize load test environment

-- Create schema
CREATE SCHEMA IF NOT EXISTS ai_fde.sales_ai_platform_loadtest;

-- Create a deterministic seed table
CREATE OR REPLACE TABLE ai_fde.sales_ai_platform_loadtest.seed_engagement_details (
    activity_id VARCHAR,
    owner_id VARCHAR,
    salesforce_account_id VARCHAR,
    activity_date DATE,
    processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
