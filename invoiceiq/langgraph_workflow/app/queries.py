CLASSIFY_QUERY = """with input_text as (
            SELECT AI_PARSE_DOCUMENT (
                TO_FILE(%(stage_name)s, %(relative_path)s),
                {{'mode': 'LAYOUT', 'page_split': false}}) AS content)
            select SNOWFLAKE.CORTEX.CLASSIFY_TEXT(content:"content", [{class_options_list}])
            as classification
            from input_text"""

GET_AI_EXTRACT_METADATA_QUERY = """SELECT 
            invoice_id
            ,banking_details
            ,due_date
            ,freight_shipping_amount
            ,invoice_currency
            ,invoice_date
            ,invoice_number
            ,memo_description
            ,payment_terms
            ,payment_type
            ,prepaid_flag
            ,purchase_order_number
            ,quantity
            ,service_end_date
            ,service_start_date
            ,shipped_to_address
            ,snowflake_entity
            ,snowflake_tax_id
            ,tax_amount
            ,total_amount
            ,unit_price
            ,vendor_address
            ,vendor_name
            ,vendor_tax_id
        FROM identifier(%(target_table)s) WHERE INVOICE_ID = %(invoice_id)s LIMIT 1"""

RUN_AI_EXTRACT_QUERY = """SELECT AI_EXTRACT(
            file => TO_FILE(%(stage_name)s, %(relative_path)s),
            responseFormat => PARSE_JSON(%(ai_extract_prompt)s)
            ) AS INVOICE_METADATA"""

RECORD_METADATA_QUERY = """
            MERGE INTO identifier(%(target_table)s) AS target
            USING (
                SELECT 
                    %(invoice_id)s as invoice_id,
                    case
                        when lower(extracted_data:payment_terms::string) = 'net 30'
                        then dateadd(day, 30, try_to_date(extracted_data:invoice_date::string, 'mm/dd/yyyy'))
                        else try_to_date(nullif(extracted_data:due_date::string, 'none'))
                    end as due_date,
                    case
                        when extracted_data:currency::string = 'us currency' then 'usd'
                        else left(extracted_data:currency::string, 10)
                    end as invoice_currency,
                    try_to_date(extracted_data:invoice_date::string, 'mm/dd/yyyy') as invoice_date,
                    extracted_data:memo_description::varchar as memo_description,
                    extracted_data:payment_terms::varchar as payment_terms,
                    extracted_data:purchase_order_number::varchar as purchase_order_number,
                    extracted_data:snowflake_entity::varchar as snowflake_entity,
                    try_cast(nullif(extracted_data:tax_amount::string, 'none') as number(38, 2)) as tax_amount,
                    try_cast(replace(extracted_data:total_amount::string, ',', '') as number(38, 2)) as total_amount,
                    extracted_data:vendor_name::varchar as vendor_name,
                    fm.ticket_number as ticket_number,
                    fm.relative_path as relative_path
                FROM (SELECT PARSE_JSON(%(json_string)s) AS extracted_data) extract_data
                JOIN invoiceiq.service.file_metadata fm ON fm.submission_id = %(invoice_id)s -- Need TICKET_NUMBER from file_metadata
            )  AS source
            ON target.invoice_id = source.invoice_id
            WHEN MATCHED THEN
                UPDATE SET
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
                    target.updated_at = current_timestamp()
            WHEN NOT MATCHED THEN
                INSERT (
                    invoice_id, 
                    ticket_number,
                    relative_path,
                    due_date, 
                    invoice_currency, 
                    invoice_date, 
                    memo_description, 
                    payment_terms, 
                    purchase_order_number, 
                    snowflake_entity, 
                    tax_amount, 
                    total_amount, 
                    vendor_name)
                VALUES (
                    source.invoice_id, 
                    source.ticket_number, 
                    source.relative_path,
                    source.due_date, 
                    source.invoice_currency, 
                    source.invoice_date, 
                    source.memo_description, 
                    source.payment_terms, 
                    source.purchase_order_number, 
                    source.snowflake_entity, 
                    source.tax_amount, 
                    source.total_amount, 
                    source.vendor_name)"""

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