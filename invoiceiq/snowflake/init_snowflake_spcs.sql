use role accountadmin;
use invoiceiq.service;

// Service owner in SPCS must have BIND SERVICE ENDPOINT on account
grant bind service endpoint on account to role invoiceiq_admin;

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