use role accountadmin;
create role if not exists <% ctx.env.admin_rl %>;
create role if not exists <% ctx.env.user_rl %>;
grant role <% ctx.env.admin_rl %> to role accountadmin;
grant role <% ctx.env.user_rl %> to role <% ctx.env.admin_rl %>;
grant create integration on account to role <% ctx.env.admin_rl %>;
grant create compute pool on account to role <% ctx.env.admin_rl %>;
grant create warehouse on account to role <% ctx.env.admin_rl %>;
grant create database on account to role <% ctx.env.admin_rl %>;
grant create application package on account to role <% ctx.env.admin_rl %>;
grant create application on account to role <% ctx.env.admin_rl %> with grant option;
grant bind service endpoint on account to role <% ctx.env.admin_rl %>;

use role <% ctx.env.admin_rl %>;
create database if not exists <% ctx.env.db %>;
create schema if not exists <% ctx.env.db %>.<% ctx.env.schema %>;
create image repository if not exists <% ctx.env.db %>.<% ctx.env.schema %>.<% ctx.env.image_repo %>;
create warehouse if not exists <% ctx.env.warehouse %> with
    warehouse_size='<% ctx.env.warehouse_size %>'
    auto_suspend = 60
    auto_resume = TRUE;
