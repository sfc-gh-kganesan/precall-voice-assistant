-- Trigger load test

-- Create processing task
CREATE OR REPLACE TASK ai_fde.sales_ai_platform_loadtest.engagement_details_processing_task
TARGET_COMPLETION_INTERVAL='10 MINUTE'
SUSPEND_TASK_AFTER_NUM_FAILURES = 3
WHEN SYSTEM$STREAM_HAS_DATA('ai_fde.sales_ai_platform_loadtest.engagement_details_stream')
AS
CALL ai_fde.sales_ai_platform_loadtest.process_engagement_details_stream();

ALTER TASK ai_fde.sales_ai_platform_loadtest.engagement_details_processing_task RESUME;

-- Execute task immediately
EXECUTE TASK ai_fde.sales_ai_platform_loadtest.engagement_details_processing_task;
