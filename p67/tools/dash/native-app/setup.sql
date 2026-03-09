create application role if not exists app_admin;
create application role if not exists app_user;
grant application role app_user to application role app_admin;

create schema if not exists app;
grant usage on schema app to application role app_admin;
grant usage on schema app to application role app_user;

create or alter versioned schema v1;
grant usage on schema v1 to application role app_admin;

-- Network rule for egress to controld public endpoint
create or replace network rule v1.controld_egress_rule
    type = HOST_PORT
    mode = EGRESS
    value_list = ('frb46h6e-sfengineering-aifde.snowflakecomputing.app:443');

-- External access integration for the dashboard service
create or replace external access integration dash_controld_eai
    allowed_network_rules = (v1.controld_egress_rule)
    enabled = true;

-- App specification for external access (consumer approval)
alter application set specification controld_access_spec
    type = EXTERNAL_ACCESS
    label = 'Connection to P67 Controld'
    description = 'Access the P67 controld backend service for workflow management'
    host_ports = ('frb46h6e-sfengineering-aifde.snowflakecomputing.app:443');

create or replace procedure v1.start_dashboard(pool_name varchar)
    returns string
    language sql
    execute as owner
as $$
begin
    create service if not exists app.dashboard
        in compute pool identifier(:pool_name)
        from specification_file='dashboard_service_spec.yml'
        external_access_integrations = (dash_controld_eai);
    grant usage on service app.dashboard to application role app_user;
    grant monitor on service app.dashboard to application role app_user;
    grant service role app.dashboard!all_endpoints_usage to application role app_user;
    return 'Dashboard service started';
end
$$;
grant usage on procedure v1.start_dashboard(varchar) to application role app_admin;

create or replace procedure v1.create_services(privileges array)
    returns string
    language sql
    execute as owner
as $$
begin
    -- Use existing compute pool - don't create our own
    -- The consumer must grant usage on a compute pool
    return 'Ready - call v1.start_dashboard(pool_name) to start the service';
end
$$;
grant usage on procedure v1.create_services(array) to application role app_admin;

create or replace procedure app.stop_dashboard()
    returns string
    language sql
    execute as owner
as $$
begin
    drop service if exists app.dashboard;
    return 'Dashboard service stopped';
end
$$;
grant usage on procedure app.stop_dashboard() to application role app_admin;

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

create or replace procedure v1.dashboard_status()
    returns string
    language sql
    execute as owner
as $$
begin
    return (select system$get_service_status('app.dashboard'));
end
$$;
grant usage on procedure v1.dashboard_status() to application role app_admin;
grant usage on procedure v1.dashboard_status() to application role app_user;

create or replace procedure v1.dashboard_logs()
    returns string
    language sql
    execute as owner
as $$
    declare logs varchar;
begin
    call system$get_service_logs('app.dashboard', '0', 'dashboard', 100) into :logs;
    return logs;
end
$$;
grant usage on procedure v1.dashboard_logs() to application role app_admin;
