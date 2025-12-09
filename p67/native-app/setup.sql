create application role if not exists app_admin;
create application role if not exists app_user;

create schema if not exists app;

grant usage on schema app to application role app_admin;
grant usage on schema app to application role app_user;

create or alter versioned schema v1;
grant usage on schema v1 to application role app_admin;

create warehouse if not exists p67_app_wh with warehouse_size='xsmall' auto_suspend = 60 auto_resume = TRUE;
grant usage on warehouse p67_app_wh to application role app_admin;
grant monitor on warehouse p67_app_wh to application role app_admin;

-- The version initializer callback is executed after a successful installation, upgrade, or
-- downgrade of an application object. In case the application fails to upgrade, the version
-- initializer of the previous (successful) version will be executed so you can clean up
-- application state that may have been modified during the failed upgrade.
create or replace procedure v1.init()
returns string
language sql
execute as owner
as
$$
begin
    alter service if exists app.harness from specification_file='services/harness/harness_spec.yaml';
    grant usage on service app.harness to application role app_user;
    grant monitor on service app.harness to application role app_user;
    return 'INIT COMPLETE';
end $$;

grant usage on procedure v1.init() to application role app_admin;

create or replace procedure v1.start_harness(pool_name varchar)
    returns string
    language sql
    as $$
begin
    create service if not exists app.harness
        in compute pool identifier(:pool_name)
        from specification_file='services/harness/harness_spec.yaml'
        query_warehouse = 'p67_app_wh';
    grant usage on service app.harness to application role app_user;
    grant monitor on service app.harness to application role app_user;
    grant service role app.harness!all_endpoints_usage to role app_user;
end
$$;

grant usage on procedure v1.start_harness(varchar) to application role app_admin;

create or replace procedure v1.create_services(privileges array)
 returns string
 language sql
 as
 $$
    begin
        create compute pool if not exists harness_compute_pool
        min_nodes = 1
        max_nodes = 1
        instance_family = cpu_x64_xs;

        call v1.start_harness('harness_compute_pool');
    end;
$$;
grant usage on procedure v1.create_services(array) to application role app_admin;


create or replace procedure app.stop_app()
    returns string
    language sql
    as
$$
begin
    drop service if exists app.harness;
end
$$;
grant usage on procedure app.stop_app() to application role app_admin;

create or replace procedure v1.app_url()
    returns string
    language sql
    as
$$
declare
    ingress_url varchar;
begin
    show endpoints in service app.harness;
    select "ingress_url" into :ingress_url from table (result_scan (last_query_id())) limit 1;
    return ingress_url;
end
$$;
grant usage on procedure v1.app_url() to application role app_admin;
grant usage on procedure v1.app_url() to application role app_user;
