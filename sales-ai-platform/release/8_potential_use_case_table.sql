-- Create a table to store potential new use cases extracted from call transcripts. 
--Each record is a single use case, so there could multiple records for a single activity.
CREATE TABLE IF NOT EXISTS ${DATABASE}.${SCHEMA}.potential_new_use_cases(
    new_use_case_id VARCHAR DEFAULT UUID_STRING(),
    record_creation_dttm DATETIME DEFAULT CURRENT_TIMESTAMP(),
    activity_date DATE,
    activity_id VARCHAR,
    owner_id VARCHAR,
    salesforce_account_id VARCHAR,
    new_use_case VARCHAR,
    status VARCHAR DEFAULT 'REVIEW',
    status_review_dttm DATETIME DEFAULT NULL
);