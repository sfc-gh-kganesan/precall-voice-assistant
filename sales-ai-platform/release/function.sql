-- Greeting workflow function
CREATE OR REPLACE FUNCTION sales_ai_greeting(name VARCHAR)
  RETURNS VARIANT
  SERVICE=${SERVICE_NAME}
  ENDPOINT=api
  AS '/greeting';

-- Arithmetic agent function (requires OPENAI_API_KEY)
CREATE OR REPLACE FUNCTION sales_ai_arithmetic(query VARCHAR)
  RETURNS VARIANT
  SERVICE=${SERVICE_NAME}
  ENDPOINT=api
  AS '/arithmetic';

-- Post meeting workflow function
CREATE OR REPLACE FUNCTION sales_ai_post_meeting(activity_id VARCHAR, owner_id VARCHAR, salesforce_account_id VARCHAR)
  RETURNS VARIANT
  SERVICE=${SERVICE_NAME}
  ENDPOINT=api
  AS '/post-meeting';

-- Submit meeting intelligence jobs
CREATE OR REPLACE FUNCTION sales_ai_meetings_jobs(args VARIANT)
  RETURNS VARIANT
  SERVICE=${SERVICE_NAME}
  ENDPOINT=api
  AS '/v1/meetings/jobs';