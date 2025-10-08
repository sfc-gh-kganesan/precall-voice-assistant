USE ROLE SYSADMIN;

SET db_name = 'INVOICEIQ';
SET schema_name = 'INVOICEIQ';
SET warehouse_name = 'DEMOWH';
SET compute_pool_name = 'DEMO_COMPUTE_POOL';
CREATE DATABASE IF NOT EXISTS IDENTIFIER($db_name);
USE DATABASE IDENTIFIER($db_name);
CREATE SCHEMA IF NOT EXISTS IDENTIFIER($schema_name);
USE SCHEMA IDENTIFIER($schema_name);

CREATE IMAGE REPOSITORY IF NOT EXISTS IMAGE_REPOSITORY;

CREATE OR REPLACE NETWORK RULE cortex_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('pm-fde.snowflakecomputing.com');

-- CREATE EXTERNAL ACCESS INTEGRATION cortex_access_integration
--   ALLOWED_NETWORK_RULES = (cortex_network_rule)
--   ENABLED = true;

CREATE OR REPLACE SECRET PAT_SECRET
  TYPE = GENERIC_STRING
  SECRET_STRING = '<SNOWFLAKE_PAT>';

DROP SERVICE IF EXISTS TICKET_PROCESSING_SERVICE;
CREATE SERVICE TICKET_PROCESSING_SERVICE
  IN COMPUTE POOL IDENTIFIER($compute_pool_name)
  EXTERNAL_ACCESS_INTEGRATIONS = (cortex_access_integration)
  FROM SPECIFICATION $$
    spec:
      containers:
      - name: ticket-processing-service
        image: /INVOICEIQ/INVOICEIQ/IMAGE_REPOSITORY/invoiceiq-agent:latest
        readinessProbe:
          port: 8000
          path: /healthcheck
        secrets:
        - snowflakeSecret: PAT_SECRET
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
WAREHOUSE = IDENTIFIER($warehouse_name)
SCHEDULE = '30 MINUTE' -- Or a CRON expression for a specific schedule
  WHEN SYSTEM$STREAM_HAS_DATA('TICKET_STREAM')
AS
MERGE INTO TICKET_METADATA_TABLE AS T
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



