USE ROLE SYSADMIN;
SET db_name = 'INVOICEIQ';
SET schema_name = 'INVOICEIQ';
SET warehouse_name = 'INVOICEIQ_WAREHOUSE';
CREATE DATABASE IF NOT EXISTS IDENTIFIER($db_name);
USE DATABASE IDENTIFIER($db_name);
CREATE SCHEMA IF NOT EXISTS IDENTIFIER($schema_name);
USE SCHEMA IDENTIFIER($schema_name);

CREATE OR ALTER TABLE INVOICE_METADATA_TABLE (
    INVOICE_ID INT AUTOINCREMENT PRIMARY KEY,
    TICKET_NUMBER VARCHAR(255) NOT NULL, -- Captures the ticket number from the submission to match with TICKET_METADATA_TABLE
    RELATIVE_PATH VARCHAR(255),
    FILE_URL varchar(1000),
    snowflake_entity VARCHAR(255),
    vendor_name VARCHAR(255),
    vendor_address VARCHAR,
    invoice_number VARCHAR(255),
    invoice_date DATE,
    total_amount NUMBER(38, 2),
    tax_amount NUMBER(38, 2),
    freight_shipping_amount NUMBER(38, 2),
    invoice_currency VARCHAR(10),
    purchase_order_number VARCHAR(255),
    banking_details VARCHAR,
    payment_terms VARCHAR(100),
    memo_description VARCHAR,
    shipped_to_address VARCHAR,
    service_start_date DATE,
    service_end_date DATE,
    quantity NUMBER(38, 4),
    unit_price NUMBER(38, 4),
    payment_type VARCHAR(50),
    due_date DATE,
    vendor_tax_id VARCHAR(100),
    snowflake_tax_id VARCHAR(100),
    prepaid_flag BOOLEAN,
    -- Optional: Add a timestamp for when the record was created
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR ALTER TABLE TICKET_METADATA_TABLE (
    ID INT AUTOINCREMENT PRIMARY KEY,
    TICKET_NUMBER VARCHAR(255) NOT NULL,
    STATUS VARCHAR(255) NOT NULL DEFAULT 'PENDING',
    AI_RESULT VARIANT
    -- AI_DECISION VARCHAR,
    -- AI_REASONING VARCHAR
);

-- Stream on top of TICKET_METADATA_TABLE to track new rows for AI processing
CREATE OR REPLACE STREAM TICKET_STREAM ON TABLE TICKET_METADATA_TABLE;