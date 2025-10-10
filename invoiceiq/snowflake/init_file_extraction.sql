use role invoiceiq_admin;
use database invoiceiq;
use schema service;

-- create stream on stage which will generate events when new files are added
create or replace stream ticket_attachments_stream on directory(@invoiceiq.service.ticket_attachments);

-- helper procedure that will consume unprocessed events in stream and dump to temporary table
-- the name of the temporary table is returned
create or replace procedure consume_stream(stream_name string)
returns string
language sql
as
$$
declare
    tbl_name string;
    sql_cmd string;
begin
    select concat(current_database(), '.', current_schema(), '.', 'stdump__', replace(:stream_name, '.', '__'), '__', date_part(epoch_millisecond, current_timestamp())) into :tbl_name;
    create temporary table identifier(:tbl_name) as select * from identifier(:stream_name) where metadata$action = 'INSERT';
    return tbl_name;
end;
$$;


-- run ai_extract on files and parse results
create or replace procedure extract_attachments(
    input_table varchar
)
returns table(
    banking_details varchar,
    due_date date,
    file_url varchar,
    freight_shipping_amount number(38, 2),
    invoice_currency varchar,
    invoice_date date,
    invoice_number varchar,
    memo_description varchar,
    payment_terms varchar,
    payment_type varchar,
    prepaid_flag boolean,
    purchase_order_number varchar,
    quantity number(38, 4),
    relative_path varchar,
    service_end_date date,
    service_start_date date,
    shipped_to_address varchar,
    snowflake_entity varchar,
    snowflake_tax_id varchar,
    tax_amount number(38, 2),
    total_amount number(38, 2),
    unit_price number(38, 4),
    vendor_address varchar,
    vendor_name varchar,
    vendor_tax_id varchar,
    _raw variant
)
language sql
as
$$
declare
    res resultset;
begin
    res := (
        with doc as (
            select 
                relative_path, 
                file_url, 
                ai_extract(to_file(file_url), {
                    'vendor_name': 'What is the name of the vendor or supplier?',
                    'invoice_number': 'What is the invoice number?',
                    'invoice_date': 'What is the date of the invoice?',
                    'total_amount': 'What is the total amount due on the invoice?',      
                    'purchase_order_number': 'What is the Purchase Order (PO) number?',
                    'banking_details': 'What are the banking details or payment instructions provided?',
                    'payment_terms': 'What are the payment terms (e.g., Net 30, Due on receipt)?',
                    'memo_description': 'Is there a memo, description, or summary of charges?',
                    'shipped_to_address': 'What is the ''Shipped To'' or delivery address?',
                    'service_start_date': 'What is the service period start date?',
                    'service_end_date': 'What is the service period end date?',
                    'quantity': 'What are the quantities for the line items listed?',
                    'unit_price': 'What are the unit prices for the line items listed?',
                    'payment_type': 'What is the suggested or required payment type (e.g., Wire, ACH, Check)?',
                    'due_date': 'What is the payment due date?',
                    'vendor_tax_id': 'What is the vendor''s Tax ID, VAT, or GST registration number?',
                    'snowflake_tax_id': 'What is Snowflake''s Tax ID or registration number on the invoice?',
                    'prepaid_flag': 'Is the invoice marked as prepaid or paid in advance?'
                }) as extracted_data 
            from 
                identifier(:input_table)
        )
        select
            extracted_data:response:banking_details::varchar as banking_details,
            case
              when extracted_data:response:payment_terms::string = 'net 30'
              then dateadd(day, 30, try_to_date(extracted_data:response:invoice_date::string, 'mm/dd/yyyy'))
              else try_to_date(nullif(extracted_data:response:due_date::string, 'none'))
            end as due_date,
            file_url,
            try_cast(nullif(extracted_data:response:freight_shipping_amount::string, 'none') as number(38, 2)) as freight_shipping_amount,
            case
              when extracted_data:response:invoice_currency::string = 'us currency' then 'usd'
              else left(extracted_data:response:invoice_currency::string, 10)
            end as invoice_currency,
            try_to_date(extracted_data:response:invoice_date::string, 'mm/dd/yyyy') as invoice_date,
            extracted_data:response:invoice_number::varchar as invoice_number,
            extracted_data:response:memo_description::varchar as memo_description,
            extracted_data:response:payment_terms::varchar as payment_terms,
            extracted_data:response:payment_type::varchar as payment_type,
            iff(lower(extracted_data:response:prepaid_flag::string) in ('yes', 'true'), true, false) as prepaid_flag,
            extracted_data:response:purchase_order_number::varchar as purchase_order_number,
            try_cast(nullif(extracted_data:response:quantity::string, 'none') as number(38, 4)) as quantity,
            relative_path,
            try_to_date(nullif(extracted_data:response:service_end_date::string, 'none')) as service_end_date,
            try_to_date(nullif(extracted_data:response:service_start_date::string, 'none')) as service_start_date,
            extracted_data:response:shipped_to_address::varchar as shipped_to_address,
            extracted_data:response:snowflake_entity::varchar as snowflake_entity,
            nullif(extracted_data:response:snowflake_tax_id::string, 'none') as snowflake_tax_id,
            try_cast(nullif(extracted_data:response:tax_amount::string, 'none') as number(38, 2)) as tax_amount,
            try_cast(replace(extracted_data:response:total_amount::string, ',', '') as number(38, 2)) as total_amount,
            try_cast(nullif(extracted_data:response:unit_price::string, 'none') as number(38, 4)) as unit_price,
            extracted_data:response:vendor_address::varchar as vendor_address,
            extracted_data:response:vendor_name::varchar as vendor_name,
            nullif(extracted_data:response:vendor_tax_id::string, 'none') as vendor_tax_id,
            extracted_data:response as _raw
        from doc
    );
    return table(res);
end;
$$;

-- run ai_extract on files in source table and merge results into
-- a target table (eg, file_metadata)
create or replace procedure extract_and_merge_attachments(
    target_table string,
    source_table string
)
returns variant
language sql
as
$$
declare
    merge_sql string;
    rows_affected int;
    stats_cursor cursor for select * from table(result_scan(last_query_id()));
begin
    merge_sql := '
        merge into identifier(''' || target_table || ''') as tgt
        using table(invoiceiq.service.extract_attachments(''' || source_table || ''')) as src
        on tgt.relative_path = src.relative_path
        when matched then
            update set
                tgt.updated_at = current_timestamp(),
                tgt.status = ''EXTRACTED'',
                tgt.extracted_fields = src._raw,
                tgt.banking_details = src.banking_details,
                tgt.due_date = src.due_date,
                tgt.file_url = src.file_url,
                tgt.freight_shipping_amount = src.freight_shipping_amount,
                tgt.invoice_currency = src.invoice_currency,
                tgt.invoice_date = src.invoice_date,
                tgt.invoice_number = src.invoice_number,
                tgt.memo_description = src.memo_description,
                tgt.payment_terms = src.payment_terms,
                tgt.payment_type = src.payment_type,
                tgt.prepaid_flag = src.prepaid_flag,
                tgt.purchase_order_number = src.purchase_order_number,
                tgt.quantity = src.quantity,
                tgt.service_end_date = src.service_end_date,
                tgt.service_start_date = src.service_start_date,
                tgt.shipped_to_address = src.shipped_to_address,
                tgt.snowflake_entity = src.snowflake_entity,
                tgt.snowflake_tax_id = src.snowflake_tax_id,
                tgt.tax_amount = src.tax_amount,
                tgt.total_amount = src.total_amount,
                tgt.unit_price = src.unit_price,
                tgt.vendor_address = src.vendor_address,
                tgt.vendor_name = src.vendor_name,
                tgt.vendor_tax_id = src.vendor_tax_id';
    
    execute immediate :merge_sql;

    open stats_cursor;
    fetch stats_cursor into rows_affected;
    close stats_cursor;
        
    return object_construct(
        'rows_affected', rows_affected
    );
end;
$$;

-- orchestrate the logic for the full extraction task:
-- a) consume new events from the ticket attachment stream and write these to a temp table
-- b) run ai_extract on each file in the temp table and merge the extracted data fields into the file_metadata table
create or replace procedure run_extraction_task(
    ticket_attachments_stream string,
    file_metadata_table string
)
returns variant
language sql
as 
$$
declare 
    attachments_processed int;
    files_updated int;
    stream_events_table string;
    merge_result variant;
    result variant;
begin
    call invoiceiq.service.consume_stream(:ticket_attachments_stream) into :stream_events_table;
    select count(*) into :attachments_processed from identifier(:stream_events_table);

    if (attachments_processed > 0) then
        call invoiceiq.service.extract_and_merge_attachments(:file_metadata_table, :stream_events_table)
        into merge_result;
        files_updated := merge_result:rows_affected;
    else
        files_updated := 0;
    end if;
       
    result := object_construct(
        'success', true,    
        'stream_events_table', :stream_events_table,
        'ticket_attachments_stream', :ticket_attachments_stream,
        'file_metadata_table', :file_metadata_table,
        'attachments_processed', :attachments_processed,
        'files_updated', :files_updated
    );

    insert into invoiceiq.service.task_execution_log (task_name, status, result)
    select 'extraction_task', 'SUCCESS', :result;

    return result;
exception
    when other then
        -- Build error result object
        result := object_construct(
            'success', false,
            'error_message', sqlerrm,
            'error_state', sqlstate,
            'stream_events_table', :stream_events_table,
            'ticket_attachments_stream', :ticket_attachments_stream,
            'file_metadata_table', :file_metadata_table,
            'attachments_processed', :attachments_processed
        );
        
        insert into invoiceiq.service.task_execution_log (task_name, status, result, error_message)
        select 'extraction_task', 'ERROR', :result, sqlerrm;
        
        return result;
end;
$$;

-- define the file extract task that will run every 1 minute when there is new stream data
create or replace task extraction_task
    warehouse = 'compute_wh'
    schedule = '1 MINUTE'
    when system$stream_has_data('invoiceiq.service.ticket_attachments_stream')
as
    call invoiceiq.service.run_extraction_task(
        'invoiceiq.service.ticket_attachments_stream',
        'invoiceiq.service.file_metadata'
    );
