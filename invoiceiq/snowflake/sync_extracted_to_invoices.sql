USE ROLE invoiceiq_admin;
USE DATABASE invoiceiq;
USE SCHEMA service;

CREATE OR REPLACE PROCEDURE INVOICEIQ.SERVICE.SYNC_EXTRACTED_TO_INVOICES()
RETURNS VARIANT
LANGUAGE SQL
AS
$$
DECLARE
    rows_inserted INT DEFAULT 0;
BEGIN
    INSERT INTO INVOICEIQ.SERVICE.INVOICES (
        relative_path,
        created_at,
        updated_at,
        status,
        submission_id,
        total_amount,
        tax_amount,
        freight_shipping_amount,
        invoice_currency,
        invoice_number,
        purchase_order_number,
        invoice_date,
        due_date,
        service_start_date,
        service_end_date,
        vendor_name,
        vendor_address,
        vendor_tax_id,
        snowflake_entity,
        snowflake_tax_id,
        shipped_to_address,
        quantity,
        unit_price,
        payment_terms,
        payment_type,
        prepaid_flag,
        banking_details,
        memo_description,
        file_url,
        ticket_number
    )
    SELECT 
        F.RELATIVE_PATH,
        CURRENT_TIMESTAMP AS CREATED_AT,
        CURRENT_TIMESTAMP AS UPDATED_AT,
        'PENDING' AS STATUS,
        F.SUBMISSION_ID,
        F.TOTAL_AMOUNT,
        F.TAX_AMOUNT,
        F.FREIGHT_SHIPPING_AMOUNT,
        F.INVOICE_CURRENCY,
        F.INVOICE_NUMBER,
        F.PURCHASE_ORDER_NUMBER,
        F.INVOICE_DATE,
        F.DUE_DATE,
        F.SERVICE_START_DATE,
        F.SERVICE_END_DATE,
        F.VENDOR_NAME,
        F.VENDOR_ADDRESS,
        F.VENDOR_TAX_ID,
        F.SNOWFLAKE_ENTITY,
        F.SNOWFLAKE_TAX_ID,
        F.SHIPPED_TO_ADDRESS,
        F.QUANTITY,
        F.UNIT_PRICE,
        F.PAYMENT_TERMS,
        F.PAYMENT_TYPE,
        F.PREPAID_FLAG,
        F.BANKING_DETAILS,
        F.MEMO_DESCRIPTION,
        F.FILE_URL,
        T.TICKET_NUMBER
    FROM INVOICEIQ.SERVICE.FILE_METADATA F
    LEFT JOIN INVOICEIQ.SERVICE.TICKET_METADATA T 
        ON F.SUBMISSION_ID = T.SUBMISSION_ID
    WHERE F.STATUS = 'EXTRACTED'
      AND NOT EXISTS (
        SELECT 1 FROM INVOICEIQ.SERVICE.INVOICES I 
        WHERE I.RELATIVE_PATH = F.RELATIVE_PATH
      );
    
    rows_inserted := SQLROWCOUNT;
    
    RETURN OBJECT_CONSTRUCT(
        'success', TRUE,
        'rows_inserted', rows_inserted,
        'message', 'Synced extracted files to invoices table'
    );
EXCEPTION
    WHEN OTHER THEN
        RETURN OBJECT_CONSTRUCT(
            'success', FALSE,
            'error_message', SQLERRM,
            'error_state', SQLSTATE
        );
END;
$$;

CREATE OR REPLACE TASK INVOICEIQ.SERVICE.SYNC_INVOICES_TASK
    WAREHOUSE = 'COMPUTE_WH'
    SCHEDULE = '2 MINUTE'
AS
    CALL INVOICEIQ.SERVICE.SYNC_EXTRACTED_TO_INVOICES();

ALTER TASK INVOICEIQ.SERVICE.SYNC_INVOICES_TASK RESUME;

