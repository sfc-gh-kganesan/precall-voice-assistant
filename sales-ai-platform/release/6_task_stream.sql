CREATE OR REPLACE STREAM ai_fde.sales_ai_platform.all_engagement_details_stream
ON TABLE sales.engagement360_pitch.all_engagement_details
APPEND_ONLY = TRUE          
SHOW_INITIAL_ROWS = FALSE;

-- Create stored procedure to process stream data
CREATE OR REPLACE PROCEDURE ai_fde.sales_ai_platform.process_engagement_details_stream()
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
  CREATE TABLE IF NOT EXISTS ai_fde.sales_ai_platform.processed_engagement_details (
    activity_id VARCHAR,
    owner_id VARCHAR,
    salesforce_account_id VARCHAR,
    activity_date DATE,
    processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
  );
  
  -- Capture timestamp BEFORE insert for precise filtering
  insert_timestamp := CURRENT_TIMESTAMP();
  
  -- INSERT from stream to advance it (and persist the batch)
  INSERT INTO ai_fde.sales_ai_platform.processed_engagement_details 
    (activity_id, owner_id, salesforce_account_id, activity_date)
  SELECT activity_id, owner_id, salesforce_account_id, activity_date
  FROM ai_fde.sales_ai_platform.all_engagement_details_stream
  WHERE type='MEETING' 
  AND raw_content IS NOT NULL
  LIMIT :batch_size;
  
  rows_processed := SQLROWCOUNT;
  
  -- Process the rows we just captured 
  IF (rows_processed > 0) THEN
    SELECT sales_ai_meetings_jobs(activity_id, owner_id, salesforce_account_id)
    FROM ai_fde.sales_ai_platform.processed_engagement_details
    WHERE processed_at >= :insert_timestamp
    ORDER BY activity_date DESC
    LIMIT :rows_processed;
  END IF;
  
  RETURN OBJECT_CONSTRUCT('status', 'success', 'rows_processed', rows_processed)::VARCHAR;
  
EXCEPTION
  WHEN OTHER THEN
    RETURN OBJECT_CONSTRUCT('status', 'error', 'message', SQLERRM)::VARCHAR;
END
$$;

-- Create task that calls the stored procedure
CREATE OR REPLACE TASK ai_fde.sales_ai_platform.all_engagement_details_task
TARGET_COMPLETION_INTERVAL='10 MINUTE'
SUSPEND_TASK_AFTER_NUM_FAILURES = 3
WHEN SYSTEM$STREAM_HAS_DATA('ai_fde.sales_ai_platform.all_engagement_details_stream')
AS
CALL ai_fde.sales_ai_platform.process_engagement_details_stream();

ALTER TASK ai_fde.sales_ai_platform.all_engagement_details_task RESUME;

