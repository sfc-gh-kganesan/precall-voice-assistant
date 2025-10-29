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
  CREATE OR REPLACE FUNCTION sales_ai_post_meeting(call_transcript VARCHAR)
    RETURNS VARIANT
    SERVICE=${SERVICE_NAME}
    ENDPOINT=api
    AS '/post-meeting';