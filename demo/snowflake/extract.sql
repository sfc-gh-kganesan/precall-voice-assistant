use role demoadmin;
use database demo;
use schema m1;

create or replace table invoices (
    invoice_id int autoincrement primary key,

    banking_details varchar,
    created_at timestamp_ntz default current_timestamp(),
    due_date date,
    file_url varchar(1000),
    freight_shipping_amount number(38, 2),
    invoice_currency varchar(10),
    invoice_date date,
    invoice_number varchar(255),
    memo_description varchar,
    payment_terms varchar(100),
    payment_type varchar(50),
    prepaid_flag boolean,
    purchase_order_number varchar(255),
    quantity number(38, 4),
    relative_path varchar(255),
    service_end_date date,
    service_start_date date,
    shipped_to_address varchar,
    snowflake_entity varchar(255),
    snowflake_tax_id varchar(100),
    tax_amount number(38, 2),
    total_amount number(38, 2),
    unit_price number(38, 4),
    vendor_address varchar,
    vendor_name varchar(255),
    vendor_tax_id varchar(100)
);

insert into invoices (
  banking_details,
  due_date,
  file_url,
  freight_shipping_amount,
  invoice_currency,
  invoice_date,
  invoice_number,
  memo_description,
  payment_terms,
  payment_type,
  prepaid_flag,
  purchase_order_number,
  quantity,
  relative_path, 
  service_end_date,
  service_start_date,
  shipped_to_address,
  snowflake_entity,
  snowflake_tax_id,
  tax_amount,
  total_amount,
  unit_price,
  vendor_address,
  vendor_name,
  vendor_tax_id
)
  select
    -- banking_details
    extracted_data:response:banking_details::varchar as banking_details,
    -- due_date
    -- calculate due date if 'net 30' and no date is found
    case
      when extracted_data:response:payment_terms::string = 'net 30'
      then dateadd(day, 30, try_to_date(extracted_data:response:invoice_date::string, 'mm/dd/yyyy'))
      else try_to_date(nullif(extracted_data:response:due_date::string, 'none'))
    end as due_date,
    -- file_url
    file_url,
    -- freight_shipping_amount
    try_cast(nullif(extracted_data:response:freight_shipping_amount::string, 'none') as number(38, 2)) as freight_shipping_amount,
    -- invoice_currency
    case
      when extracted_data:response:invoice_currency::string = 'us currency' then 'usd'
      else left(extracted_data:response:invoice_currency::string, 10)
    end as invoice_currency,
    -- invoice_date
    TRY_TO_DATE(extracted_data:response:invoice_date::STRING, 'MM/DD/YYYY') as invoice_date,
    -- invoice_number
    extracted_data:response:invoice_number::VARCHAR as invoice_number,
    -- memo_description
    extracted_data:response:memo_description::varchar as memo_description,
    -- payment_terms
    extracted_data:response:payment_terms::varchar as payment_terms,
    -- payment_type
    extracted_data:response:payment_type::varchar as payment_type,
    -- prepaid_flag
    iff(lower(extracted_data:response:prepaid_flag::string) in ('yes', 'true'), true, false) as prepaid_flag,
    -- purchase_order_number
    extracted_data:response:purchase_order_number::varchar as purchase_order_number,
    -- quantity
    try_cast(nullif(extracted_data:response:quantity::string, 'none') as number(38, 4)) as quantity,
    -- relative_path
    relative_path,
    -- service_end_date
    try_to_date(nullif(extracted_data:response:service_end_date::string, 'none')) as service_end_date,
    -- service_start_date
    try_to_date(nullif(extracted_data:response:service_start_date::string, 'none')) as service_start_date,
    -- shipped_to_address
    extracted_data:response:shipped_to_address::varchar as shipped_to_address,
    -- snowflake_entity
    extracted_data:response:snowflake_entity::varchar as snowflake_entity,
    -- snowflake_tax_id
    nullif(extracted_data:response:snowflake_tax_id::string, 'none') as snowflake_tax_id,
    -- tax_amount
    try_cast(nullif(extracted_data:response:tax_amount::string, 'none') as number(38, 2)) as tax_amount,
    -- total_amount
    try_cast(replace(extracted_data:response:total_amount::string, ',', '') as number(38, 2)) as total_amount,
    -- unit_price
    try_cast(nullif(extracted_data:response:unit_price::string, 'none') as number(38, 4)) as unit_price,
    -- vendor_address
    extracted_data:response:vendor_address::varchar as vendor_address,
    -- vendor_name
    extracted_data:response:vendor_name::varchar as vendor_name,
    -- vendor_tax_id
    nullif(extracted_data:response:vendor_tax_id::string, 'none') as vendor_tax_id,
  from (
    select 
      relative_path, 
      file_url, 
      ai_extract(to_file(file_url), {
        'snowflake_entity': 'What is the Snowflake entity or company name being billed?',
        'vendor_name': 'What is the name of the vendor or supplier?',
        'vendor_address': 'What is the full address of the vendor?',
        'invoice_number': 'What is the invoice number?',
        'invoice_date': 'What is the date of the invoice?',
        'total_amount': 'What is the total amount due on the invoice?',
        'tax_amount': 'What is the total tax amount (e.g., GST, VAT, Sales Tax)?',
        'freight_shipping_amount': 'What is the freight or shipping cost?',
        'invoice_currency': 'What is the currency of the invoice amounts (e.g., USD, EUR, CAD)?',
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
    from directory(@demo.m1.test_data) 
    where relative_path like 'golden_invoices/%.pdf'
  );
