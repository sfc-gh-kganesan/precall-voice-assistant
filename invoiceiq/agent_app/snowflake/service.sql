use role invoiceiq_admin;
use invoiceiq.service;

drop service if exists ticket_processing_service;
// Env var is temporary fix for SNOWFLAKE_ACCOUNT due to SPCS container not having access to SNOWFLAKE_HOST endpoint
CREATE SERVICE TICKET_PROCESSING_SERVICE
  IN COMPUTE POOL COMPUTE_POOL_CPU
  EXTERNAL_ACCESS_INTEGRATIONS = (cortex_access_integration)
  FROM SPECIFICATION $$
    spec:
      containers:
      - name: ticket-processing-service
        image: /INVOICEIQ/SERVICE/IMAGE_REPOSITORY/invoiceiq-agent:latest
        readinessProbe:
          port: 8000
          path: /healthcheck
        env:
          SNOWFLAKE_PSEUDO_ACCOUNT: sfengineering-aifde
        secrets:
        - snowflakeSecret: INVOICEIQ_SECRET
          secretKeyRef: secret_string
          envVarName: 'SNOWFLAKE_PAT'
      endpoints:
      - name: ticketendpoint
        port: 8000
        public: true
      $$
  --  MIN_INSTANCES=1
  --  MAX_INSTANCES=1
   ;

DESC SERVICE TICKET_PROCESSING_SERVICE;

-- Create a SERVICE FUNCTION for processing tickets
CREATE OR REPLACE FUNCTION PROCESS_TICKET (ticket_number VARCHAR)
  RETURNS VARIANT
  SERVICE=TICKET_PROCESSING_SERVICE
  ENDPOINT=ticketendpoint
  AS '/process';

-- Create a TASK to process new rows in the TICKET_STREAM
CREATE OR REPLACE TASK PROCESS_TICKET_TASK
WAREHOUSE = compute_wh
SCHEDULE = '30 MINUTE' -- Or a CRON expression for a specific schedule
  WHEN SYSTEM$STREAM_HAS_DATA('TICKET_STREAM')
AS
MERGE INTO TICKET_METADATA AS T
USING (
    SELECT
        S.ID,
        -- Call the service function here, passing necessary data.
        -- Use PARSE_JSON() if the service function returns a JSON string.
        PROCESS_TICKET(
           S.TICKET_NUMBER
        ) AS PROCESS_TICKET_RESULT
    FROM TICKET_STREAM AS S
    -- We are only interested in updates/inserts
    WHERE S.METADATA$ACTION IN ('INSERT', 'UPDATE')
    AND S.STATUS = 'READY'
) AS S_PROCESSED
ON T.ID = S_PROCESSED.ID -- Assuming 'ID' is the primary key for matching

-- Update the record in the target table
WHEN MATCHED THEN
    UPDATE SET
        T.AI_RESULT = S_PROCESSED.PROCESS_TICKET_RESULT,
        T.LAST_PROCESSED_TS = CURRENT_TIMESTAMP()
;

ALTER TASK PROCESS_TICKET_TASK RESUME;



