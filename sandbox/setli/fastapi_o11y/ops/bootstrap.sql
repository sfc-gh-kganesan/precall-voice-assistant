CREATE DATABASE IF NOT EXISTS <% ctx.env.DATABASE %>;

CREATE SCHEMA IF NOT EXISTS <% ctx.env.DATABASE ~ '.' ~ ctx.env.SCHEMA %>;

CREATE STAGE IF NOT EXISTS <% ctx.env.DATABASE ~ '.' ~ ctx.env.SCHEMA ~ '.' ~ ctx.env.STAGE %>
  DIRECTORY=(enable=true auto_refresh=true) 
  ENCRYPTION=(type='SNOWFLAKE_SSE');

-- Note: creating compute pool from SQL because there is no clean way to do "create or replace" action from SnowCLI
CREATE COMPUTE POOL IF NOT EXISTS <% ctx.env.COMPUTE_POOL %>
    MIN_NODES = 1
    MAX_NODES = 1
    INSTANCE_FAMILY = CPU_X64_XS
    AUTO_RESUME = true
    INITIALLY_SUSPENDED = true
    AUTO_SUSPEND_SECS = 60;

-- Note: creating image repository from SQL because there is no clean way to do "create or replace" action from SnowCLI
CREATE IMAGE REPOSITORY IF NOT EXISTS <% ctx.env.DATABASE ~ '.' ~ ctx.env.SCHEMA ~ '.' ~ ctx.env.IMAGE_REPOSITORY %>;

