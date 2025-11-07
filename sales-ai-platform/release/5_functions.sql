-- Post meeting workflow function
CREATE OR REPLACE FUNCTION ${DATABASE}.${SCHEMA}.sales_ai_post_meeting(activity_id VARCHAR, owner_id VARCHAR, salesforce_account_id VARCHAR)
  RETURNS VARIANT
  SERVICE=${DATABASE}.${SCHEMA}.${SERVICE_NAME}
  ENDPOINT=api
  AS '/post-meeting';

-- Submit meeting intelligence jobs
CREATE OR REPLACE FUNCTION ${DATABASE}.${SCHEMA}.sales_ai_meetings_jobs(args VARIANT)
  RETURNS VARIANT
  SERVICE=${DATABASE}.${SCHEMA}.${SERVICE_NAME}
  ENDPOINT=api
  AS '/v1/meetings/jobs';

-- Grant usage on functions to roles defined in USAGE_ROLES environment variable
BEGIN
  LET roles STRING := '${USAGE_ROLES}';
  LET role_array ARRAY := SPLIT(:roles, ',');
  FOR i IN 0 TO ARRAY_SIZE(:role_array) - 1 DO
    LET current_role STRING := TRIM(GET(:role_array, :i));
    EXECUTE IMMEDIATE 'GRANT USAGE ON FUNCTION ${DATABASE}.${SCHEMA}.sales_ai_post_meeting(VARCHAR, VARCHAR, VARCHAR) TO ROLE ' || :current_role;
    EXECUTE IMMEDIATE 'GRANT USAGE ON FUNCTION ${DATABASE}.${SCHEMA}.sales_ai_meetings_jobs(VARIANT) TO ROLE ' || :current_role;
  END FOR;
END;