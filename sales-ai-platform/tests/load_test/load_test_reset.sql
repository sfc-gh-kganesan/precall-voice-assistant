-- Reset load test environment

-- Check if schema exists to prevent errors
CREATE SCHEMA IF NOT EXISTS ai_fde.sales_ai_platform_loadtest;

-- truncate all tables in the schema
CREATE TABLE IF NOT EXISTS ai_fde.sales_ai_platform_loadtest.seed_engagement_details (
    activity_id VARCHAR,
    owner_id VARCHAR,
    salesforce_account_id VARCHAR,
    activity_date DATE,
    processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
TRUNCATE TABLE ai_fde.sales_ai_platform_loadtest.seed_engagement_details;

CREATE TABLE IF NOT EXISTS ai_fde.sales_ai_platform_loadtest.processed_engagement_details (
    activity_id VARCHAR,
    owner_id VARCHAR,
    salesforce_account_id VARCHAR,
    activity_date DATE,
    processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
TRUNCATE TABLE ai_fde.sales_ai_platform_loadtest.processed_engagement_details;

CREATE TABLE IF NOT EXISTS ai_fde.sales_ai_platform_loadtest.udf_debug_results (
    result VARIANT,
    processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
TRUNCATE TABLE ai_fde.sales_ai_platform_loadtest.udf_debug_results;

-- Reset stream
DROP STREAM IF EXISTS ai_fde.sales_ai_platform_loadtest.engagement_details_stream;

CREATE STREAM ai_fde.sales_ai_platform_loadtest.engagement_details_stream
ON TABLE ai_fde.sales_ai_platform_loadtest.seed_engagement_details
APPEND_ONLY = TRUE
SHOW_INITIAL_ROWS = FALSE;
