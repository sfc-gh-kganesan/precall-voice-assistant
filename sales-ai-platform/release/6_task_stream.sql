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
  payload VARIANT;
BEGIN
  -- build a compact batch payload from the stream rows
  SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
  INTO :payload
  FROM ai_fde.sales_ai_platform.all_engagement_details_stream
  WHERE type='MEETING' 
  AND raw_content is not null
  LIMIT 1000; -- TODO: Remove this limit once we have validated the approach

  -- send to sales_ai_meetings_jobs function
  SELECT sales_ai_meetings_jobs(:payload);

  -- advance the stream offset without persisting rows
  -- TODO: advance the offset only by the amount of rows processed above
  CREATE OR REPLACE TEMP TABLE _noop LIKE sales.engagement360_pitch.all_engagement_details;
  INSERT INTO _noop
    SELECT * EXCLUDE (METADATA$ACTION, METADATA$ISUPDATE, METADATA$ROW_ID)
    FROM ai_fde.sales_ai_platform.all_engagement_details_stream
    WHERE FALSE;
  
  RETURN 'Success';
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

