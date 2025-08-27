use role accountadmin;

create role if not exists demoadmin;
create warehouse if not exists demowh with
  warehouse_size = 'XSMALL'
  auto_suspend = 10
  auto_resume = true
  comment = 'warehouse for light queries.';

grant usage on warehouse demowh to role demoadmin;
grant create database on account to role demoadmin;

grant role demoadmin to user setli;
alter user setli set default role = demoadmin;

grant role demoadmin to user nwiegand;
alter user nwiegand set default role = demoadmin;

use role demoadmin;
select current_user();
select current_role();

create database if not exists demo;
create schema if not exists demo.m1;
create stage if not exists demo.m1.test_data 
  directory=(enable=true auto_refresh=true) 
  encryption=(type='SNOWFLAKE_SSE');

