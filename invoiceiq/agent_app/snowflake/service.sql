use role invoiceiq_admin;
use invoiceiq.service;

drop service if exists invoice_processing_service;
// Env var is temporary fix for SNOWFLAKE_ACCOUNT due to SPCS container not having access to SNOWFLAKE_HOST endpoint
CREATE SERVICE invoice_PROCESSING_SERVICE
  IN COMPUTE POOL COMPUTE_POOL_CPU
  EXTERNAL_ACCESS_INTEGRATIONS = (cortex_access_integration)
  QUERY_WAREHOUSE = COMPUTE_WH
  MIN_INSTANCES=1
  MAX_INSTANCES=1
  FROM SPECIFICATION $$
    spec:
      containers:
      - name: invoice-processing-service
        image: /INVOICEIQ/SERVICE/IMAGE_REPOSITORY/invoiceiq-agent:latest
        readinessProbe:
          port: 8000
          path: /healthcheck
      endpoints:
      - name: invoiceendpoint
        port: 8000
        public: true
      $$
   ;

DESC SERVICE INVOICE_PROCESSING_SERVICE;

-- Create a SERVICE FUNCTION for processing invoices
CREATE OR REPLACE FUNCTION PROCESS_INVOICE (invoice_id VARCHAR)
  RETURNS VARIANT
  SERVICE=INVOICE_PROCESSING_SERVICE
  ENDPOINT=invoiceendpoint
  AS '/process';

CREATE OR REPLACE TASK consume_invoices_stream_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '5 MINUTE'
AS
-- This single, atomic statement drains the stream and queues the data.
INSERT INTO INVOICE_PROCESSING_QUEUE (
    INVOICE_ID,
    AI_PROCESSED_AT,
    METADATA$ACTION,
    METADATA$ISUPDATE
)
SELECT
    INVOICE_ID,
    AI_PROCESSED_AT,
    METADATA$ACTION,
    METADATA$ISUPDATE
FROM INVOICEIQ.SERVICE.INVOICES_STREAM
WHERE
    -- This condition ensures we only grab records that represent new data (new inserts or the 'after' image of an update)
    METADATA$ACTION = 'INSERT'
    -- This is the crucial condition that prevents the infinite loop.
    -- It ignores changes that were caused by our own processor task.
AND AI_PROCESSED_AT IS NULL;

-- Create a TASK to process new rows in the INVOICE_PROCESSING_QUEUE
-- Task will process one invoice at a time to avoid batched failures from one invoice error
-- Task has to delete the invoice from the queue table after processing to avoid infinite loop
CREATE OR REPLACE TASK process_and_cleanup_invoice_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '1 MINUTE'
AS
BEGIN
    -- This block will hold the results of processing a single invoice
    DECLARE
        v_invoice_id VARCHAR;
        v_ai_decision VARCHAR;
        v_ai_reasoning VARCHAR;
    BEGIN
        -- Step 1: Find one invoice, process it, parse it, and store the results in variables.
        -- NOTE: This reads from the QUEUE TABLE, not the raw stream, for reliability.
        WITH
            AGENT_RESULTS AS (
                SELECT
                    -- Call the function on the ID from the queue table
                    PARSE_JSON(PROCESS_INVOICE(INVOICE_ID)) AS RAW_RESULTS
                FROM INVOICE_PROCESSING_QUEUE -- Reading from the safe queue table
                LIMIT 1 -- Process only one record per task run
            ),
            PROCESSED_RESULTS AS (
                -- Parse the JSON results from the previous step
                SELECT
                    RAW_RESULTS:"ai_decision"::VARCHAR AS AI_DECISION,
                    RAW_RESULTS:"ai_reasoning"::VARCHAR AS AI_REASONING,
                    RAW_RESULTS:"invoice_id"::VARCHAR AS INVOICE_ID
                FROM AGENT_RESULTS
            )
        -- Put the final, parsed results into our variables
        SELECT
            INVOICE_ID,
            AI_DECISION,
            AI_REASONING
        INTO
            :v_invoice_id,
            :v_ai_decision,
            :v_ai_reasoning
        FROM PROCESSED_RESULTS;

        -- Step 2: Only proceed if we actually found and processed an invoice
        IF (v_invoice_id IS NOT NULL) THEN
            -- Step 3: Merge the results into the main INVOICES table
            MERGE INTO INVOICEIQ.SERVICE.INVOICES AS T
            USING (
                SELECT
                    :v_invoice_id AS INVOICE_ID,
                    :v_ai_decision AS AI_DECISION,
                    :v_ai_reasoning AS AI_REASONING
            ) AS S
            ON T.INVOICE_ID = S.INVOICE_ID
            WHEN MATCHED THEN
                UPDATE SET
                    T.AI_DECISION = S.AI_DECISION,
                    T.AI_REASONING = S.AI_REASONING,
                    T.AI_PROCESSED_AT = CURRENT_TIMESTAMP();

            -- Step 4: Atomically delete the processed record from the queue table
            DELETE FROM INVOICE_PROCESSING_QUEUE
            WHERE INVOICE_ID = :v_invoice_id;

            RETURN 'Successfully processed and cleaned up invoice: ' || :v_invoice_id;
        ELSE
            RETURN 'No invoices to process in the queue table.';
        END IF;
    END;
END;


-- Tasks start in suspended state
-- ALTER TASK consume_invoices_stream_task RESUME;
-- ALTER TASK process_and_cleanup_invoice_task RESUME;