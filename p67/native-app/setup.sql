create application role if not exists app_admin;
create application role if not exists app_user;
grant application role app_user to application role app_admin;

create schema if not exists app;
grant usage on schema app to application role app_admin;
grant usage on schema app to application role app_user;

create or alter versioned schema v1;
grant usage on schema v1 to application role app_admin;

create warehouse if not exists p67_app_wh with warehouse_size='xsmall' auto_suspend = 60 auto_resume = TRUE;
grant usage on warehouse p67_app_wh to application role app_admin;
grant usage on warehouse p67_app_wh to application role app_user;
grant monitor on warehouse p67_app_wh to application role app_admin;


execute immediate from 'register_callbacks.sql';
execute immediate from 'configure_callbacks.sql';

-- The version initializer callback is executed after a successful installation, upgrade, or
-- downgrade of an application object. In case the application fails to upgrade, the version
-- initializer of the previous (successful) version will be executed so you can clean up
-- application state that may have been modified during the failed upgrade.
create or replace procedure v1.init()
    returns string
    language sql
    execute as owner
as $$
begin
    alter service if exists app.controld from specification_file='controld_service_spec.yml';
    alter service if exists app.controld set external_access_integrations=( reference('google_oauth_eai'), reference('postgres_eai') );
    return 'INIT COMPLETE';
end
$$;

grant usage on procedure v1.init() to application role app_admin;

create or replace procedure v1.start_controld(pool_name varchar)
    returns string
    language sql
    execute as owner
as $$
begin
    create service if not exists app.controld
        in compute pool identifier(:pool_name)
        from specification_file='controld_service_spec.yml'
        external_access_integrations=( reference('google_oauth_eai'), reference('postgres_eai') )
        query_warehouse = 'p67_app_wh';
    grant usage on service app.controld to application role app_user;
    grant monitor on service app.controld to application role app_user;
    grant service role app.controld!all_endpoints_usage to application role app_user;
    return 'START COMPLETE';
end
$$;
grant usage on procedure v1.start_controld(varchar) to application role app_admin;

create or replace procedure v1.create_services(privileges array)
    returns string
    language sql
    execute as owner
as $$
begin
    create compute pool if not exists service_compute_pool
    min_nodes = 1
    max_nodes = 5
    instance_family = cpu_x64_xs;
    grant usage on compute pool service_compute_pool to application role app_user;
    grant usage on compute pool service_compute_pool to application role app_admin;

    call v1.start_controld('service_compute_pool');
    return 'CREATE_SERVICES COMPLETE';
end
$$;
grant usage on procedure v1.create_services(array) to application role app_admin;

create or replace procedure app.stop_app()
    returns string
    language sql
    execute as owner
as $$
begin
    drop service if exists app.controld;
    return 'STOP_APP COMPLETE';
end
$$;
grant usage on procedure app.stop_app() to application role app_admin;

create or replace procedure v1.app_url()
    returns string
    language sql
    execute as owner
as $$
    declare ingress_url varchar;
begin
    show endpoints in service app.controld;
    select "ingress_url" into :ingress_url from table (result_scan (last_query_id())) limit 1;
    return ingress_url;
end
$$;
grant usage on procedure v1.app_url() to application role app_admin;
grant usage on procedure v1.app_url() to application role app_user;
