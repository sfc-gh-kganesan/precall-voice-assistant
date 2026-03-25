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
    declare
        controld_url varchar;
        controld_dns varchar;
begin
    begin
        alter service if exists app.controld from specification_file='controld_service_spec.yml';
        alter service if exists app.controld set external_access_integrations=( reference('google_oauth_eai'), reference('snowflake_egress_eai'), reference('postgres_eai') );

        show services like 'CONTROLD' in schema app;
        select "dns_name" into :controld_dns from table(result_scan(last_query_id())) limit 1;
        controld_url := '"http://' || controld_dns || ':80"';
        alter service if exists app.dashboard from specification_template_file='dashboard_service_spec.yml'
            using (controld_url => :controld_url);
    exception
        when other then
            -- New references (e.g. encryption_key) may not be bound yet during upgrade.
            -- The service will be updated once the consumer binds the missing references
            -- and calls start_controld or re-runs init.
            return 'INIT PARTIAL — service not updated: ' || sqlerrm;
    end;

    -- Explicitly resume the runner compute pool. Exclusive app-owned pools
    -- with auto_resume=true should auto-resume when EXECUTE JOB SERVICE is
    -- called, but in practice the pool can get stuck in SUSPENDED state
    -- indefinitely — the job never registers (num_jobs stays 0) and the
    -- pool never provisions a node. ACCOUNTADMIN cannot ALTER an exclusive
    -- app-owned pool, so the only fix is to resume from within the app.
    -- Running this on every INIT (i.e. every deploy) ensures the pool is
    -- ready before any workflow runs.
    begin
        alter compute pool if exists runner_compute_pool resume;
    exception
        when other then null; -- Pool may already be active
    end;

    -- Create service function after the service has been updated with the webhook endpoint
    begin
        create or replace function app.trigger_new_user_workflow(row_data variant)
            returns variant
            service = app.controld
            endpoint = web
            as '/api/webhook/snowflake/NEW_USER';
        grant usage on function app.trigger_new_user_workflow(variant) to application role app_admin;
        grant usage on function app.trigger_new_user_workflow(variant) to application role app_user;
    exception
        when other then
            -- Service may not have the webhook endpoint yet
            return 'INIT PARTIAL — service function not created: ' || sqlerrm;
    end;

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
        external_access_integrations=( reference('google_oauth_eai'), reference('snowflake_egress_eai'), reference('postgres_eai') )
        query_warehouse = 'p67_app_wh';
    grant usage on service app.controld to application role app_user;
    grant monitor on service app.controld to application role app_user;
    grant service role app.controld!all_endpoints_usage to application role app_user;
    grant service role app.controld!webhook_caller to application role app_admin;
    return 'START COMPLETE';
end
$$;
grant usage on procedure v1.start_controld(varchar) to application role app_admin;

create or replace procedure v1.start_dashboard(pool_name varchar)
    returns string
    language sql
    execute as owner
as $$
    declare
        controld_url varchar;
        controld_dns varchar;
begin
    show services like 'CONTROLD' in schema app;
    select "dns_name" into :controld_dns from table(result_scan(last_query_id())) limit 1;
    controld_url := '"http://' || controld_dns || ':80"';

    create service if not exists app.dashboard
        in compute pool identifier(:pool_name)
        from specification_template_file='dashboard_service_spec.yml'
        using (controld_url => :controld_url)
        query_warehouse = 'p67_app_wh';
    grant usage on service app.dashboard to application role app_user;
    grant monitor on service app.dashboard to application role app_user;
    grant service role app.dashboard!all_endpoints_usage to application role app_user;
    return 'DASHBOARD START COMPLETE';
end
$$;
grant usage on procedure v1.start_dashboard(varchar) to application role app_admin;

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

    create compute pool if not exists runner_compute_pool
    min_nodes = 1
    max_nodes = 10
    instance_family = cpu_x64_xs;
    grant usage on compute pool runner_compute_pool to application role app_admin;

    create stage if not exists app.workflow_stage
        encryption = (type = 'SNOWFLAKE_SSE');

    call v1.start_controld('service_compute_pool');
    call v1.start_dashboard('service_compute_pool');
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
    drop service if exists app.dashboard;
    drop service if exists app.controld force;
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

create or replace procedure v1.dashboard_url()
    returns string
    language sql
    execute as owner
as $$
    declare ingress_url varchar;
begin
    show endpoints in service app.dashboard;
    select "ingress_url" into :ingress_url from table (result_scan (last_query_id())) limit 1;
    return ingress_url;
end
$$;
grant usage on procedure v1.dashboard_url() to application role app_admin;
grant usage on procedure v1.dashboard_url() to application role app_user;
