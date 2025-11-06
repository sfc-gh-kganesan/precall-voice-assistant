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