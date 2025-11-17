DROP SERVICE IF EXISTS <% SPCS_DATABASE_NAME %>.<% SPCS_SCHEMA_NAME %>.<% KB_BUILDER_SVC_NAME %>;

CREATE SERVICE <% SPCS_DATABASE_NAME %>.<% SPCS_SCHEMA_NAME %>.<% KB_BUILDER_SVC_NAME %>
IN COMPUTE POOL <% SPCS_COMPUTE_POOL_NAME %>
FROM SPECIFICATION $$
spec:
  containers:
  - name: kb-builder-container
    image: <% SPCS_REPO_URL %>/<% KB_BUILDER_IMAGE_NAME %>:latest
  endpoints:
  - name: api
    port: 8000
    public: true
  platformMonitor:
    metricConfig:
      groups:
      - system
      - system_limits
$$
AUTO_RESUME = TRUE
MIN_INSTANCES = 1
MAX_INSTANCES = 1
QUERY_WAREHOUSE = <% SPCS_WAREHOUSE_NAME %>
EXTERNAL_ACCESS_INTEGRATIONS = (<% SPCS_EAI_NAME %>);

