-- p67-dash Native App Setup Script

-- Create application schema
CREATE SCHEMA IF NOT EXISTS app;

-- Create image repository stage
CREATE STAGE IF NOT EXISTS app.images
  DIRECTORY = (ENABLE = TRUE)
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

-- Application roles
CREATE APPLICATION ROLE IF NOT EXISTS app_admin;
CREATE APPLICATION ROLE IF NOT EXISTS app_viewer;

-- Compute pool (will be created by consumer if needed)
CREATE OR REPLACE PROCEDURE app.create_compute_pool(pool_name VARCHAR, warehouse_size VARCHAR DEFAULT 'X-SMALL')
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  EXECUTE IMMEDIATE 'CREATE COMPUTE POOL IF NOT EXISTS ' || pool_name || 
    ' MIN_NODES = 1 MAX_NODES = 1' ||
    ' INSTANCE_FAMILY = CPU_X64_' || warehouse_size;
  RETURN 'Compute pool ' || pool_name || ' created successfully';
END;
$$;

-- Service creation procedure
CREATE OR REPLACE PROCEDURE app.start_dashboard_service(
  compute_pool_name VARCHAR,
  p67_endpoint VARCHAR DEFAULT 'controld.ghw6if.svc.spcs.internal:80'
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
  service_name VARCHAR := 'app.dashboard_service';
BEGIN
  -- Create the dashboard service
  EXECUTE IMMEDIATE '
    CREATE SERVICE IF NOT EXISTS ' || service_name || '
    IN COMPUTE POOL ' || compute_pool_name || '
    FROM SPECIFICATION $$
    spec:
      containers:
        - name: dashboard
          image: /app/images/dashboard:latest
          env:
            P67_API_URL: http://' || p67_endpoint || '
          readinessProbe:
            path: /health
            port: 3001
      endpoints:
        - name: dashboard
          port: 3001
          public: true
    $$
  ';
  
  RETURN 'Dashboard service started on compute pool ' || compute_pool_name;
END;
$$;

-- Stop service procedure
CREATE OR REPLACE PROCEDURE app.stop_dashboard_service()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  DROP SERVICE IF EXISTS app.dashboard_service;
  RETURN 'Dashboard service stopped';
END;
$$;

-- Reference registration callback for p67 controld
CREATE OR REPLACE PROCEDURE app.register_p67_reference(ref_name VARCHAR, operation VARCHAR, ref_or_alias VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  CASE operation
    WHEN 'ADD' THEN
      -- Grant access to the p67 controld service
      SELECT SYSTEM$SET_REFERENCE(:ref_name, :ref_or_alias);
      RETURN 'Reference ' || ref_name || ' registered successfully';
    WHEN 'REMOVE' THEN
      RETURN 'Reference ' || ref_name || ' removed';
    WHEN 'CLEAR' THEN
      RETURN 'References cleared';
    ELSE
      RETURN 'Unknown operation: ' || operation;
  END CASE;
END;
$$;

-- Get service URL procedure
CREATE OR REPLACE PROCEDURE app.get_dashboard_url()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
  url VARCHAR;
BEGIN
  SELECT SYSTEM$GET_SERVICE_STATUS('app.dashboard_service') INTO url;
  RETURN url;
END;
$$;

-- Grant privileges to app_admin
GRANT USAGE ON SCHEMA app TO APPLICATION ROLE app_admin;
GRANT ALL PRIVILEGES ON ALL PROCEDURES IN SCHEMA app TO APPLICATION ROLE app_admin;
GRANT USAGE ON STAGE app.images TO APPLICATION ROLE app_admin;

-- Grant read-only privileges to app_viewer
GRANT USAGE ON SCHEMA app TO APPLICATION ROLE app_viewer;
GRANT USAGE ON PROCEDURE app.get_dashboard_url() TO APPLICATION ROLE app_viewer;
