use role accountadmin;
use invoiceiq.service;

// Service owner in SPCS must have BIND SERVICE ENDPOINT on account
grant bind service endpoint on account to role invoiceiq_admin;

// Grant permission for SPCS to access Snowflake REST API from within container
create or replace network rule snowflake_egress_access
  mode = egress
  type = host_port
  value_list = ('sfengineering-aifde.snowflakecomputing.com');
create or replace external access integration snowflake_egress_access_integration
  allowed_network_rules = (snowflake_egress_access)
  enabled = true;
grant usage on integration snowflake_egress_access_integration to role invoiceiq_admin;

// Bypass requirement for user to have network policy when using PAT
create authentication policy enforced_not_required
    pat_policy=(
        network_policy_evaluation = ENFORCED_NOT_REQUIRED
    );
alter user if exists svc_invoiceiq set authentication policy enforced_not_required;
alter user if exists svc_invoiceiq add programmatic access token invoiceiq_token
    role_restriction = 'INVOICEIQ_ADMIN';
// PAT will be passed via Snowflake secret to SPCS container
create or replace secret invoiceiq_secret
  type = generic_string
  secret_string = '<SNOWFLAKE_PAT>'; -- Need to enter actual PAT from above PAT creation statement

grant read on secret invoiceiq_secret to role invoiceiq_admin;

// Create image repository for SPCS to pull docker image from
create image repository if not exists image_repository;
grant read on image repository image_repository to role invoiceiq_admin;
grant write on image repository image_repository to role invoiceiq_admin;

// Create compute pool (for SPCS) and warehouse (for tasks)
create compute pool if not exists COMPUTE_POOL_CPU
  min_nodes = 1
  max_nodes = 1
  instance_family = CPU_X64_S;
grant usage, monitor on compute pool COMPUTE_POOL_CPU to role invoiceiq_admin;
create warehouse if not exists compute_wh
  warehouse_size = 'XSMALL'
  auto_suspend = 10
  auto_resume = true;
grant usage on warehouse compute_wh to role invoiceiq_admin;