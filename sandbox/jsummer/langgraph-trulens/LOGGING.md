# Logging and Tracing in Snowpark Container Services

This document provides recipes for surfacing observability data from applications running in Snowpark Container Services (SPCS). It covers retrieving:

- **Application Logs** — Standard log output from your containerized application
- **Application Traces** — Spans and events captured via OpenTelemetry
- **Custom Span Attributes** — Explicit trace attributes added by your application
- **TruLens Traces** — Curated traces specific to TruLens evaluation workflows

---

## Prerequisites

Before logs and traces can be captured and queried, ensure the following:

1. **Install the Snowflake Telemetry SDK**  
   Add [snowflake-telemetry-python](https://pypi.org/project/snowflake-telemetry-python/) to your application dependencies. This package is required for both logging and tracing.

2. **Enable Logging in Snowsight**  
   Set the log level to `ON` at the account or `database.schema` level via Snowsight.

3. **Configure an Event Table**  
   Ensure an event table (default or explicit) is set for your account or database to capture telemetry data.

---

> [!NOTE]
> A note on tracing for SPCS before we begin: See function `setup_tracing()` in `utils.py` for initializing an OpenTelemetry tracer that is compatible with SPCS. Most notably, it uses gRPC for the OTLP exporter, not HTTP. In addition, SPCS automatically sets environment variable `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` to specify the endpoint for exporting traces.

## Application Logs

### Querying Event Table for an SPCS Service Logs

Use the following SQL to retrieve application logs from the event table. This query extracts the log message, severity level, service metadata, and any custom log extras.

```sql
SELECT 
  VALUE as logged_msg, -- Logged message including severity prefix for pythonic logging, e.g. INFO
  RECORD['severity_text'] as log_level,
  RESOURCE_ATTRIBUTES['snow.service.name'] as service_name,
  RESOURCE_ATTRIBUTES['snow.service.container.name'] as container_name,
  CASE WHEN
    OBJECT_DELETE(RECORD_ATTRIBUTES,
    'code.filepath', 'code.function','code.lineno', 'log.iostream') = OBJECT_CONSTRUCT() THEN NULL
    ELSE OBJECT_DELETE(RECORD_ATTRIBUTES,
    'code.filepath', 'code.function','code.lineno', 'log.iostream')
  END AS custom_log_extras,
  *
FROM
  IDENTIFIER($event_table_name)
WHERE 1=1
  AND RECORD_TYPE = 'LOG'
  AND DATE(timestamp) = DATE(CURRENT_DATE())
  AND SCOPE['name'] = 'jsummer-langgraph' -- logger name
  AND RESOURCE_ATTRIBUTES['snow.database.name'] = 'JSUMMER' -- Database namespace of the service
  AND RESOURCE_ATTRIBUTES['snow.schema.name'] = 'SANDBOX' -- Schema namespace of the service
ORDER BY TIMESTAMP DESC;
```

---

## Traces

Traces are captured in the Snowflake event table alongside logs. This includes spans from TruLens instrumentation, LangGraph workflows, and any custom application traces.

### Querying Event Table for an SPCS Service Traces

All traces are captured in the Snowflake event table. 
Custom trace attributes are extracted from `RECORD_ATTRIBUTES`.
The scope helps to determine the origin of the trace. 
A `SCOPE.name` of `trulens` captures the implicit traces produces by TruLens.
Alternatively, a `SCOPE.name` that mirrors the `instrumenting_module_name` in your Tracer object corresponds to your application-level tracing explicitly set in your application.

This query isolates custom span attributes added by your application, filtering out standard instrumentation prefixes (`ai.observability.*`, `db.*`, `code.*`, `method.*`).

```sql
WITH FilteredKeyValues AS (
    SELECT
        t.TRACE['span_id'] as span_id,
        t.SCOPE['name'] as trace_scope,
        f.key,
        f.value
    FROM
        IDENTIFIER($event_table_name) t,
        LATERAL FLATTEN(
            INPUT => t.RECORD_ATTRIBUTES,
            MODE => 'OBJECT'
        ) f
    WHERE
        NOT (
        f.key LIKE 'ai.observability.%' OR
        f.key LIKE 'db.%' OR
        f.key LIKE 'code.%' OR
        f.key LIKE 'method.%'
    )
),
AggregatedAttributes AS (
    SELECT
        span_id,
        OBJECT_AGG(key, value) AS filtered_record_attributes
    FROM
        FilteredKeyValues
    GROUP BY
        span_id
)
SELECT
    t.RECORD_ATTRIBUTES['ai.observability.graph_node.node_name'] AS node_name,
    t.TRACE['span_id'] as span_id,
    t.TRACE['trace_id'] as trace_id,
    a.filtered_record_attributes as custom_span_attributes,
    t.*
FROM
    IDENTIFIER($event_table_name) t
LEFT JOIN
    AggregatedAttributes a ON t.TRACE['span_id'] = a.span_id
WHERE 1=1
    AND t.RECORD_TYPE IN ('SPAN', 'SPAN_EVENT')
    AND DATE(t.timestamp) = CURRENT_DATE()
ORDER BY
    t.TIMESTAMP DESC;
```

### TruLens Traces via SDK

The TruLens SDK provides the `get_record_details()` method to extract curated traces for a given run. These traces include only data required for TruLens reporting and do not include custom application traces.
This method is a curated rendering of the TruLens traces captured above directly from the event table. 

```python
from evals import langgraph_workflow  # TruGraph instance containing the run

runs = langgraph_workflow.list_runs()
most_recent_run_name = runs[-1].run_name

run_record = langgraph_workflow.get_run(run_name=most_recent_run_name)
run_details = run_record.get_record_details()  # Returns a pandas DataFrame
run_details.to_csv("run_details.csv")
```

