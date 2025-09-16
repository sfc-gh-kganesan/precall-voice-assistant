use role accountadmin;

create role if not exists demoadmin;
create warehouse if not exists demowh with
  warehouse_size = 'XSMALL'
  auto_suspend = 10
  auto_resume = true
  comment = 'warehouse for light queries.';

grant usage on warehouse demowh to role demoadmin;
grant create database on account to role demoadmin;
grant bind service endpoint on account to role demoadmin;

create compute pool if not exists demo_compute_pool
  min_nodes = 1
  max_nodes = 1
  instance_family = cpu_x64_xs;

grant usage, monitor on compute pool demo_compute_pool to role demoadmin;

grant role demoadmin to user setli;
grant role demoadmin to user nwiegand;

use role demoadmin;
select current_user();
select current_role();

create database if not exists demo;
create schema if not exists demo.m1;
create stage if not exists demo.m1.test_data 
  directory=(enable=true auto_refresh=true) 
  encryption=(type='SNOWFLAKE_SSE');

use database demo;
use schema m1;
create image repository if not exists images;

