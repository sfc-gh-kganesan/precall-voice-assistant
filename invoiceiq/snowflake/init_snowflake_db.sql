use role accountadmin;
create role if not exists invoiceiq_admin;
grant role invoiceiq_admin to role accountadmin;
create database if not exists invoiceiq;
grant ownership on database invoiceiq to role invoiceiq_admin;

grant role invoiceiq_admin to user jsummer;
grant role invoiceiq_admin to user setli;
grant role invoiceiq_admin to user vsrinivas;

use role invoiceiq_admin;
create schema if not exists invoiceiq.service;
create stage if not exists invoiceiq.service.ticket_attachments
  directory=(enable=true auto_refresh=true) 
  encryption=(type='SNOWFLAKE_SSE');

create table if not exists invoiceiq.service.file_metadata (
    created_at timestamp_ntz default current_timestamp,
    extracted_fields variant,
    relative_path varchar,
    status varchar default 'PENDING',
    submission_id varchar, -- FK to ticket_metadata table
    updated_at timestamp_ntz default current_timestamp

    -- banking_details varchar,
    -- due_date date,
    -- file_url varchar,
    -- freight_shipping_amount number(38, 2),
    -- invoice_currency varchar,
    -- invoice_date date,
    -- invoice_number varchar,
    -- memo_description varchar,
    -- payment_terms varchar,
    -- payment_type varchar,
    -- prepaid_flag boolean,
    -- purchase_order_number varchar,
    -- quantity number(38, 4),
    -- relative_path varchar,
    -- service_end_date date,
    -- service_start_date date,
    -- shipped_to_address varchar,
    -- snowflake_entity varchar,
    -- snowflake_tax_id varchar,
    -- tax_amount number(38, 2),
    -- total_amount number(38, 2),
    -- unit_price number(38, 4),
    -- vendor_address varchar,
    -- vendor_name varchar,
    -- vendor_tax_id varchar
);

create table if not exists invoiceiq.service.ticket_metadata (
    created_at timestamp_ntz default current_timestamp,
    status varchar default 'PENDING',
    ticket_number varchar,
    submission_id varchar,
    updated_at timestamp_ntz default current_timestamp,
    email varchar,
    ai_result variant,
    ai_decision varchar,
    ai_reasoning varchar
);

create stream if not exists invoiceiq.service.ticket_stream 
  on table invoiceiq.service.ticket_metadata;