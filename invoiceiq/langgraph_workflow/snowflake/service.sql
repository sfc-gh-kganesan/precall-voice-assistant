use role invoiceiq_admin;
use invoiceiq.service;

drop service if exists invoice_processing_service;

CREATE SERVICE invoice_PROCESSING_SERVICE
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