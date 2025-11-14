CLASSIFY_QUERY = """with input_text as (
            SELECT AI_PARSE_DOCUMENT (
                TO_FILE(%(stage_name)s, %(relative_path)s),
                {{'mode': 'LAYOUT', 'page_split': false}}) AS content)
            select 
                SNOWFLAKE.CORTEX.CLASSIFY_TEXT(content:"content", [{class_options_list}]) as classification,
                content:"content"::string as parsed_text
            from input_text"""

GET_AI_EXTRACT_METADATA_QUERY = """SELECT 
            invoice_id
            ,due_date
            ,invoice_currency
            ,invoice_date
            ,memo_description
            ,payment_terms
            ,purchase_order_number
            ,snowflake_entity
            ,tax_amount
            ,total_amount
            ,vendor_name
        FROM identifier(%(target_table)s) WHERE INVOICE_ID = %(invoice_id)s LIMIT 1"""

RUN_AI_EXTRACT_QUERY = """with ai_extract_result as (
SELECT AI_EXTRACT(
  file => TO_FILE(%(stage_name)s, %(relative_path)s),
  responseFormat => PARSE_JSON(%(ai_extract_prompt)s)
) as invoice_metadata)
SELECT 
    OBJECT_CONSTRUCT(*) as invoice_metadata
    FROM (
        SELECT
        invoice_metadata:response:snowflake_entity::STRING AS "snowflake_entity",
        invoice_metadata:response:vendor_name::STRING AS "vendor_name",
        PARSE_DATE(invoice_metadata:response:invoice_date::STRING) AS "invoice_date",
        ROUND(REGEXP_REPLACE(invoice_metadata:response:total_amount, '[^0-9]', '')::INT /100::DECIMAL(38,2), 2) AS "total_amount",
        ROUND(REGEXP_REPLACE(invoice_metadata:response:tax_amount, '[^0-9]', '')::INT /100::DECIMAL(38,2), 2) AS "tax_amount",
        invoice_metadata:response:currency::STRING AS "invoice_currency",
        'PO-' || REGEXP_REPLACE(invoice_metadata:response:purchase_order_number::STRING, '[^0-9]', '') AS "purchase_order_number",
        invoice_metadata:response:payment_terms::STRING AS "payment_terms",
        CASE
            -- 1. Try to use the due_date field directly
            WHEN PARSE_DATE(invoice_metadata:response:due_date::STRING) IS NOT NULL
                THEN PARSE_DATE(invoice_metadata:response:due_date::STRING)

            -- 2. Calculate due_date based on invoice_date and payment_terms
            WHEN PARSE_DATE(invoice_metadata:response:invoice_date::STRING) IS NOT NULL
                AND invoice_metadata:response:payment_terms::STRING IS NOT NULL
                THEN
                    CASE
                        WHEN LOWER(invoice_metadata:response:payment_terms::STRING) = 'net 30'
                            THEN DATEADD(DAY, 30, PARSE_DATE(invoice_metadata:response:invoice_date::STRING))
                        WHEN LOWER(invoice_metadata:response:payment_terms::STRING) = 'net 60'
                            THEN DATEADD(DAY, 60, PARSE_DATE(invoice_metadata:response:invoice_date::STRING))
                        WHEN LOWER(invoice_metadata:response:payment_terms::STRING) = 'net 45'
                            THEN DATEADD(DAY, 45, PARSE_DATE(invoice_metadata:response:invoice_date::STRING))
                        WHEN LOWER(invoice_metadata:response:payment_terms::STRING) in ('due upon receipt', 'immediate')
                            THEN PARSE_DATE(invoice_metadata:response:invoice_date::STRING)
                        ELSE NULL
                    END
            ELSE NULL
        END AS "due_date",
        invoice_metadata:response:memo_description::STRING AS "memo_description"
FROM ai_extract_result
)"""

RECORD_METADATA_QUERY = """
            MERGE INTO identifier(%(target_table)s) AS target
            USING (
                SELECT 
                    %(invoice_id)s as invoice_id,
                    extracted_data:invoice_number::varchar as invoice_number,
                    TRY_TO_DATE(extracted_data:due_date::string) as due_date,
                    COALESCE(extracted_data:invoice_currency, extracted_data:currency)::varchar as invoice_currency,
                    TRY_TO_DATE(extracted_data:invoice_date::string) as invoice_date,
                    extracted_data:memo_description::varchar as memo_description,
                    extracted_data:payment_terms::varchar as payment_terms,
                    extracted_data:purchase_order_number::varchar as purchase_order_number,
                    extracted_data:snowflake_entity::varchar as snowflake_entity,
                    extracted_data:tax_amount::decimal(38,2) as tax_amount,
                    extracted_data:total_amount::decimal(38,2) as total_amount,
                    extracted_data:vendor_name::varchar as vendor_name,
                    PARSE_JSON(%(bounding_boxes_string)s) as bounding_boxes,
                    PARSE_JSON(%(fields_with_bounding_boxes_string)s) as fields_with_bounding_boxes,
                    fm.ticket_number as ticket_number,
                    fm.relative_path as relative_path
                FROM (SELECT PARSE_JSON(%(json_string)s) AS extracted_data) extract_data
                JOIN invoiceiq.service.file_metadata fm ON fm.submission_id = %(invoice_id)s -- Need TICKET_NUMBER from file_metadata
            )  AS source
            ON target.invoice_id = source.invoice_id
            WHEN MATCHED THEN
                UPDATE SET
                    target.invoice_number = source.invoice_number,
                    target.due_date = source.due_date,
                    target.invoice_currency = source.invoice_currency,
                    target.invoice_date = source.invoice_date,
                    target.memo_description = source.memo_description,
                    target.payment_terms = source.payment_terms,
                    target.purchase_order_number = source.purchase_order_number,
                    target.snowflake_entity = source.snowflake_entity,
                    target.tax_amount = source.tax_amount,
                    target.total_amount = source.total_amount,
                    target.vendor_name = source.vendor_name,
                    target.bounding_boxes = source.bounding_boxes,
                    target.fields_with_bounding_boxes = source.fields_with_bounding_boxes,
                    target.updated_at = current_timestamp()
            WHEN NOT MATCHED THEN
                INSERT (
                    invoice_id, 
                    ticket_number,
                    relative_path,
                    invoice_number,
                    due_date, 
                    invoice_currency, 
                    invoice_date, 
                    memo_description, 
                    payment_terms, 
                    purchase_order_number, 
                    snowflake_entity, 
                    tax_amount, 
                    total_amount, 
                    vendor_name,
                    bounding_boxes,
                    fields_with_bounding_boxes)
                VALUES (
                    source.invoice_id, 
                    source.ticket_number, 
                    source.relative_path,
                    source.invoice_number,
                    source.due_date, 
                    source.invoice_currency, 
                    source.invoice_date, 
                    source.memo_description, 
                    source.payment_terms, 
                    source.purchase_order_number, 
                    source.snowflake_entity, 
                    source.tax_amount, 
                    source.total_amount, 
                    source.vendor_name,
                    source.bounding_boxes,
                    source.fields_with_bounding_boxes)"""

GET_PURCHASE_ORDER_HEADER_METADATA_QUERY = """SELECT 
        * 
        FROM INVOICEIQ.SERVICE.PURCHASE_ORDER
        where PO_HEADER_NUMBER = %(purchase_order_number)s"""

GET_PURCHASE_ORDER_LINE_ITEM_METADATA_QUERY = """SELECT 
        * 
        FROM INVOICEIQ.SERVICE.PURCHASE_ORDER_LINE_ITEM
        where PO_HEADER_NUMBER = %(purchase_order_number)s"""

RECORD_AI_DECISION_QUERY = """
        UPDATE identifier(%(target_table)s)
        SET AI_DECISION = %(ai_decision)s, AI_REASONING = %(ai_reasoning)s, AI_PROCESSED_AT = CURRENT_TIMESTAMP()
        WHERE INVOICE_ID = %(invoice_id)s"""

GET_FULL_TEXT_QUERY = """
        SELECT AI_PARSE_DOCUMENT (
            TO_FILE(%(stage_name)s, %(relative_path)s),
            {'mode': 'LAYOUT', 'page_split': false}
        ) AS content"""

GET_PDF_FILE_QUERY = """
        SELECT GET_PRESIGNED_URL(%(stage_name)s, %(relative_path)s, 3600) AS presigned_url"""
