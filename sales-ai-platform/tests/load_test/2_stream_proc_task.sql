-- Set up stream and processing task

-- Create stream
CREATE OR REPLACE STREAM ai_fde.sales_ai_platform_loadtest.engagement_details_stream
ON TABLE ai_fde.sales_ai_platform_loadtest.seed_engagement_details
APPEND_ONLY = TRUE
SHOW_INITIAL_ROWS = FALSE;

-- Create stored procedure to process stream data
CREATE OR REPLACE PROCEDURE ai_fde.sales_ai_platform_loadtest.process_engagement_details_stream()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
    rows_processed INTEGER DEFAULT 0;
    batch_size INTEGER DEFAULT 100;
    insert_timestamp TIMESTAMP_NTZ;
BEGIN
    -- Create tracking table to advance stream offset
    CREATE TABLE IF NOT EXISTS ai_fde.sales_ai_platform_loadtest.processed_engagement_details (
        activity_id VARCHAR,
        owner_id VARCHAR,
        salesforce_account_id VARCHAR,
        activity_date DATE,
        processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    );

    CREATE TABLE IF NOT EXISTS ai_fde.sales_ai_platform_loadtest.udf_debug_results (
        result VARIANT,
        processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    );

    -- Capture timestamp BEFORE insert for precise filtering
    insert_timestamp := CURRENT_TIMESTAMP();
    
    -- INSERT from stream to advance it (and persist the batch)
    INSERT INTO ai_fde.sales_ai_platform_loadtest.processed_engagement_details 
        (activity_id, owner_id, salesforce_account_id, activity_date)
    SELECT activity_id, owner_id, salesforce_account_id, activity_date
    FROM ai_fde.sales_ai_platform_loadtest.engagement_details_stream
    LIMIT :batch_size;
    
    rows_processed := SQLROWCOUNT;

    -- call the real Sales AI endpoint for load testing
    INSERT INTO ai_fde.sales_ai_platform_loadtest.udf_debug_results (result)
    SELECT ai_fde.sales_ai_platform.sales_ai_meetings_jobs(
        activity_id,
        owner_id,
        salesforce_account_id
    )
    FROM ai_fde.sales_ai_platform_loadtest.processed_engagement_details
    WHERE processed_at >= :insert_timestamp;

    RETURN OBJECT_CONSTRUCT('status','success','rows_processed',rows_processed)::VARCHAR;

EXCEPTION
    WHEN OTHER THEN
        RETURN OBJECT_CONSTRUCT('status','error','message',SQLERRM)::VARCHAR;
END;
$$;
