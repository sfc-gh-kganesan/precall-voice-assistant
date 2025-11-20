DROP SERVICE IF EXISTS ${DATABASE}.${SCHEMA}.${SERVICE_NAME};

CREATE SERVICE ${DATABASE}.${SCHEMA}.${SERVICE_NAME}
IN COMPUTE POOL ${COMPUTE_POOL}
FROM SPECIFICATION $$
spec:
  containers:
  - name: ${CONTAINER_NAME}
    image: ${REPO_URL}/${IMAGE_NAME}:${IMAGE_TAG}
    env:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LANGSMITH_TRACING: ${LANGSMITH_TRACING}
      LANGSMITH_API_KEY: ${LANGSMITH_API_KEY}
      LANGSMITH_PROJECT: ${LANGSMITH_PROJECT}
      LANGSMITH_ENDPOINT: ${LANGSMITH_ENDPOINT}
      LLM_PROVIDER: ${LLM_PROVIDER}
      METAORCHESTRATOR_AUTH_EMAIL: ${METAORCHESTRATOR_AUTH_EMAIL}
      DEMO_MODE: ${DEMO_MODE}
      DBOS_SYSTEM_DATABASE_URL: "sqlite:////sfmnt/dbos.db"
    volumeMounts:
    - name: shared-data
      mountPath: /sfmnt
  endpoints:
  - name: api
    port: 8000
    public: true
  platformMonitor:
    metricConfig: # change this to add more metrics (refer to the snowflake docs)
      groups:
      - system
      - system_limits
  volumes:
  - name: shared-data
    source: local
$$
AUTO_RESUME = TRUE
MIN_INSTANCES = 1
MAX_INSTANCES = 1
QUERY_WAREHOUSE = ${SNOWFLAKE_WAREHOUSE}
EXTERNAL_ACCESS_INTEGRATIONS = (${EXTERNAL_ACCESS_INTEGRATION});
