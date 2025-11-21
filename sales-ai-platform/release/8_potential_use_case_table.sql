-- Create a table to store potential new use cases extracted from call transcripts. 
--Each record is a single use case, so there could multiple records for a single activity.
CREATE OR REPLACE TABLE  ${DATABASE}.${SCHEMA}.potential_new_use_cases(
    new_use_case_id VARCHAR DEFAULT UUID_STRING(),
    record_creation_dttm DATETIME DEFAULT CURRENT_TIMESTAMP(),
    activity_date DATE,
    activity_id VARCHAR,
    owner_id VARCHAR,
    salesforce_account_id VARCHAR,
    use_case_description VARCHAR,
    use_case_name VARCHAR,
    workloads ARRAY,
    technical_use_cases ARRAY,
    incumbent_vendor VARCHAR,
    status VARCHAR DEFAULT 'REVIEW',
    status_review_dttm DATETIME DEFAULT NULL,
    sfdc_use_case_id VARCHAR DEFAULT NULL,
    last_updated_dttm DATETIME DEFAULT NULL,
    last_update_by VARCHAR DEFAULT NULL
);