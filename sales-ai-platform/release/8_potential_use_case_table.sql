-- Create a table to store potential new use cases extracted from call transcripts. 
-- Each record is a single use case, so there could multiple records for a single activity.
-- NOTE: Could consider adding a storage lifecycle policy to this table to automatically delete old records after a certain period of time.
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

-- Grant privileges to the roles that need access to this table.
GRANT SELECT ON TABLE ${DATABASE}.${SCHEMA}.potential_new_use_cases TO ROLE SFDC_SALES_AI_RO_RL;
GRANT UPDATE ON TABLE ${DATABASE}.${SCHEMA}.potential_new_use_cases TO ROLE SFDC_SALES_AI_RO_RL;
GRANT USAGE ON DATABASE ${DATABASE} TO ROLE SFDC_SALES_AI_RO_RL;
GRANT USAGE ON SCHEMA ${DATABASE}.${SCHEMA} TO ROLE SFDC_SALES_AI_RO_RL;

GRANT SELECT ON TABLE ${DATABASE}.${SCHEMA}.potential_new_use_cases TO ROLE IT_ADV_RO;
GRANT UPDATE ON TABLE ${DATABASE}.${SCHEMA}.potential_new_use_cases TO ROLE IT_ADV_RO;
GRANT USAGE ON DATABASE ${DATABASE} TO ROLE IT_ADV_RO;
GRANT USAGE ON SCHEMA ${DATABASE}.${SCHEMA} TO ROLE IT_ADV_RO;