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

create stream if not exists attachment_stream on stage invoiceiq.service.ticket_attachments;

create table if not exists invoiceiq.service.file_metadata (
    created_at timestamp_ntz default current_timestamp,
    relative_path varchar,
    submission_id varchar, -- FK to ticket_metadata table
    ticket_number varchar -- Maps to ticket_metadata table
);

create table if not exists invoiceiq.service.ticket_metadata (
    created_at timestamp_ntz default current_timestamp,
    status varchar default 'PENDING',
    ticket_number varchar,
    submission_id varchar,
    updated_at timestamp_ntz default current_timestamp,
    email varchar
);