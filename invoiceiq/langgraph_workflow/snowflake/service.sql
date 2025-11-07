use role invoiceiq_admin;
use invoiceiq.service;

-- Parse Date UDF for unpacking AI_EXTRACT_METADATA
CREATE OR REPLACE FUNCTION parse_date(date_string STRING)
  RETURNS DATE
  LANGUAGE PYTHON
  PACKAGES = ('python-dateutil')
  RUNTIME_VERSION = '3.12'
  HANDLER = 'parse_date'
AS $$
from dateutil import parser
from datetime import date
def parse_date(date_string):
    try:
        date_object = parser.parse(date_string).date()
        return date_object
    except ValueError:
        return None 
$$;

drop service if exists INVOICE_PROCESSING_SERVICE;

CREATE SERVICE INVOICE_PROCESSING_SERVICE
  IN COMPUTE POOL COMPUTE_POOL_CPU
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
-- TODO: Add use_existing_ai_extract parameter with default value of false
CREATE OR REPLACE FUNCTION PROCESS_INVOICE (target_table VARCHAR, invoice_id VARCHAR, relative_path VARCHAR, stage_name VARCHAR)
  RETURNS VARIANT
  SERVICE=INVOICE_PROCESSING_SERVICE
  ENDPOINT=invoiceendpoint
  AS '/process';

-- Stored  procedure used here instead of directly processing stream results because we need to consume the stream results.
-- To do so, we create a temporary table to insert into.
CREATE OR REPLACE PROCEDURE PROCESS_INVOICES_STREAM()
RETURNS TABLE (
  invoice_id VARCHAR,
  processing_status VARIANT
)
LANGUAGE SQL
AS
$$
DECLARE
  STREAM_NAME VARCHAR DEFAULT 'INVOICEIQ.SERVICE.ATTACHMENT_STREAM';
  TARGET_TABLE VARCHAR DEFAULT 'INVOICEIQ.SERVICE.INVOICES';
  STAGE_NAME VARCHAR DEFAULT 'INVOICEIQ.SERVICE.TICKET_ATTACHMENTS';
  
BEGIN
    CREATE OR REPLACE TEMPORARY TABLE temp_processed_results (
      invoice_id VARCHAR,
      processing_status VARIANT
    );

    INSERT INTO temp_processed_results (invoice_id, processing_status)
    SELECT 
      FM.SUBMISSION_ID,
      PARSE_JSON(PROCESS_INVOICE(
        :TARGET_TABLE, -- Target table with invoice data to retrieve and write
        FM.SUBMISSION_ID, -- Becomes INVOICE_ID in the target table
        STREAM.RELATIVE_PATH,
        :STAGE_NAME -- Stage name for ticket attachments; Will also accept with '@'
      ))
    FROM IDENTIFIER(:STREAM_NAME) STREAM
    JOIN FILE_METADATA FM ON FM.RELATIVE_PATH = STREAM.RELATIVE_PATH
    WHERE STREAM.METADATA$ACTION = 'INSERT' AND NOT STREAM.METADATA$ISUPDATE; -- We only process net new attachments, not updates

    LET res RESULTSET := (SELECT * FROM temp_processed_results);
    RETURN TABLE(res);
END;
$$;

CREATE OR REPLACE TASK process_invoices_stream_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '2 MINUTE' -- A single invocation can take roughly up to 2 minutes to complete
  WHEN SYSTEM$STREAM_HAS_DATA('ATTACHMENT_STREAM')
AS
CALL PROCESS_INVOICES_STREAM();

ALTER TASK process_invoices_stream_task RESUME;