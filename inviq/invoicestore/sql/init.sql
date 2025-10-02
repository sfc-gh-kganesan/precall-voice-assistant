-- initialize invoicestore sqlite database
-- database: invoicestore

create table if not exists submission (
    id integer primary key,
    created_at datetime default current_timestamp,
    lift_ticket text,
    file_ids text check (json_valid(file_ids)),
    status text not null
);


create table if not exists invoice (
    id integer primary key,
    created_at datetime default current_timestamp,
    lift_ticket text,
    file_id text text,
    status text not null,
    status_desc text,
    vendor_name text,
    invoice_number text,
    invoice_date text,
    total_amount text,
    purchase_order_number text,
    banking_details text,
    payment_terms text,
    memo_description text,
    shipped_to_address text,
    service_start_date text,
    service_end_date text,
    quantity text,
    unit_price text,
    payment_type text,
    due_date text,
    vendor_tax_id text,
    snowflake_tax_id text,
    prepaid_flag text
);

