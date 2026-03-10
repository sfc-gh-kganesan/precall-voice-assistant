# Trigger Workflow from Snowflake Table

Set up a Snowflake stream, service function, and task to automatically trigger a P67 workflow whenever rows are inserted into a table.

## Overview

This skill walks through creating all the Snowflake objects needed to wire a table insert event to a controld workflow run via the Snowflake webhook endpoint (`POST /api/webhook/snowflake/:workflowName`).

The architecture:

```
Table INSERT
    -> Stream (captures new rows)
        -> Task (polls stream, fires when data exists)
            -> Service Function (in-cluster HTTP call to controld)
                -> Controld webhook endpoint (sync by default)
                    -> Workflow run with row data as params
                        -> Result returned to SQL caller
```

## Two Modes: SPCS Service Function vs External Function

### SPCS Service Function (preferred)

When controld runs on SPCS, use a **service function**. This makes an in-cluster HTTP call — no API integration, no bearer token, no external network hop. Auth is handled by SPCS service roles.

### External Function (external controld)

When controld runs outside Snowflake (e.g. local Docker, external cloud), use a traditional **external function** with an API integration and bearer token. See the "External Function Alternative" section at the end.

## Prerequisites

- The controld service is deployed on SPCS (for service function path)
- The Snowflake webhook endpoint is available at `/api/webhook/snowflake/:workflowName`
- The target workflow is deployed to controld and set to **Public** visibility
- The service spec includes `serviceRoles` with a `webhook_caller` role granting access to the `web` endpoint

## Information to Gather

Before starting, ask the user for:

1. **Source table** — The fully qualified table name (e.g. `DB.SCHEMA.USERS`). Then pull its schema with `DESCRIBE TABLE` to discover column names and types.
2. **Workflow name** — The name of the deployed P67 workflow to trigger (e.g. `NEW_USER`). This must match the workflow name in controld exactly.
3. **Workflow parameters** — Which columns from the table should be passed as params to the workflow. By default, pass all columns. The user may want to rename or exclude some.
4. **Warehouse** — The warehouse to use for the task.
5. **Task schedule** — How often the task should check for new data (default: relies on `WHEN` clause, checks every 1 minute).
6. **Log table** — Whether to create a log table to capture results. Recommended.

## Step 1: Create the Stream

Create an append-only stream on the source table. Append-only streams only capture inserts, which is typically what you want for triggering workflows.

```sql
CREATE OR REPLACE STREAM <schema>.{table_name}_stream
    ON TABLE <fully_qualified_table>
    APPEND_ONLY = TRUE;
```

**Notes:**
- `APPEND_ONLY = TRUE` means only INSERT operations are captured (not UPDATE or DELETE).
- If the user also needs to trigger on updates/deletes, use a standard stream (omit `APPEND_ONLY`) and filter with `METADATA$ACTION` in the task query.

## Step 2: Create the Service Function

For SPCS deployments, create a service function that routes to the controld webhook endpoint:

```sql
CREATE OR REPLACE FUNCTION <schema>.trigger_{workflow_name}_workflow(row_data VARIANT)
    RETURNS VARIANT
    SERVICE = <app_schema>.controld
    ENDPOINT = web
    AS '/api/webhook/snowflake/<WORKFLOW_NAME>';
```

Grant usage to the roles that need it:

```sql
GRANT USAGE ON FUNCTION <schema>.trigger_{workflow_name}_workflow(VARIANT) TO ROLE <role_name>;
```

**Important:**
- The workflow name in the URL path must match exactly (case-sensitive).
- No API integration or bearer token needed — SPCS handles auth via service roles.
- The service spec must define a `serviceRoles` entry granting the calling role access to the `web` endpoint.

### Service Spec Requirements

In `controld_service_spec.yml`, ensure the service roles section exists:

```yaml
serviceRoles:
    - name: webhook_caller
      endpoints:
          - web
```

And grant the service role to the app role that owns the task:

```sql
GRANT SERVICE ROLE <app_schema>.controld!webhook_caller TO APPLICATION ROLE <role>;
```

## Step 3: Create the Log Table (Recommended)

Create a table to capture the workflow results:

```sql
CREATE TABLE IF NOT EXISTS <schema>.{workflow_name}_log (
    TRIGGERED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    {key_columns from source table, e.g. USER_ID VARCHAR, USER_NAME VARCHAR},
    RESULT VARIANT
);
```

The `RESULT` column stores the full workflow response as a VARIANT, which includes `runId`, `status`, `exitCode`, and the workflow `result` object.

## Step 4: Create the Task

**Critical: The task must use DML (INSERT INTO), not a bare SELECT.** A bare `SELECT` from a stream reads the data but does NOT advance the stream offset. Only DML statements (`INSERT`, `MERGE`, `CTAS`) in a committed transaction consume the stream.

```sql
CREATE OR REPLACE TASK <schema>.process_{table_name}_inserts
    WAREHOUSE = <warehouse>
    SCHEDULE = '1 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('<fully_qualified_stream>')
AS
    INSERT INTO <schema>.{workflow_name}_log ({key_columns}, RESULT)
    SELECT
        {key_column_expressions},
        <schema>.trigger_{workflow_name}_workflow(
            OBJECT_CONSTRUCT(
                {column_mappings}
            )
        )
    FROM <fully_qualified_stream>
    WHERE METADATA$ACTION = 'INSERT';
```

The `{column_mappings}` should be built from the table schema. For each column the user wants to pass:

```sql
OBJECT_CONSTRUCT(
    'COLUMN_NAME_1', COLUMN_NAME_1::VARCHAR,
    'COLUMN_NAME_2', COLUMN_NAME_2::VARCHAR,
    ...
)
```

**Cast all values to VARCHAR** since the workflow `params` object is `Record<string, string>`.

**Notes:**
- `WHEN SYSTEM$STREAM_HAS_DATA(...)` makes this event-driven: the task body only executes when there are new rows. No data = no compute = no cost.
- The `INSERT INTO ... SELECT` is DML, which correctly consumes the stream.
- For append-only streams, the `WHERE METADATA$ACTION = 'INSERT'` filter is technically redundant but harmless and makes intent clear.

## Step 5: Resume the Task

Tasks are created in a suspended state. Enable it:

```sql
ALTER TASK <schema>.process_{table_name}_inserts RESUME;
```

Verify it's running:

```sql
SHOW TASKS LIKE 'process_{table_name}_inserts' IN SCHEMA <schema>;
```

## Step 6: Test the Setup

Insert a test row into the source table:

```sql
INSERT INTO <fully_qualified_table> (<columns>) VALUES (<test_values>);
```

Then verify:

1. **Stream has data** (before the task runs):
   ```sql
   SELECT * FROM <fully_qualified_stream>;
   ```
   (Should show the new row. After the task runs, the stream will be empty.)

2. **Task ran successfully:**
   ```sql
   SELECT *
   FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
       TASK_NAME => 'PROCESS_{TABLE_NAME}_INSERTS',
       SCHEDULED_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())
   ))
   ORDER BY SCHEDULED_TIME DESC
   LIMIT 5;
   ```

3. **Log table has the result:**
   ```sql
   SELECT * FROM <schema>.{workflow_name}_log ORDER BY TRIGGERED_AT DESC LIMIT 5;
   ```
   The `RESULT` column should contain the full workflow output, e.g.:
   ```json
   {
     "exitCode": 0,
     "result": { "NAME": "Test User", "REVERSED_NAME": "resU tseT" },
     "runId": "abc-123",
     "status": "completed"
   }
   ```

## Sync vs Async Mode

The webhook endpoint is **synchronous by default**: it awaits workflow completion and returns the full result in the Snowflake batch response. This is the right choice for most service function use cases since the result lands directly in the log table.

For long-running workflows that might exceed Snowflake's timeout (10 minutes for external functions, configurable via `BATCH_TIMEOUT_SECS` for service functions), use async mode:

```sql
-- Service function pointing to async endpoint
CREATE OR REPLACE FUNCTION <schema>.trigger_{workflow_name}_workflow_async(row_data VARIANT)
    RETURNS VARIANT
    SERVICE = <app_schema>.controld
    ENDPOINT = web
    AS '/api/webhook/snowflake/<WORKFLOW_NAME>?mode=async';
```

In async mode, the function returns immediately with `{ "runId": "...", "status": "running" }` and the workflow completes in the background. The caller must poll for results separately.

## Troubleshooting

### Stream never drains (task runs but stream keeps growing)
- **Most common cause:** The task uses a bare `SELECT` instead of DML. Only DML (`INSERT INTO`, `MERGE`, `CREATE TABLE AS SELECT`) in a committed transaction consumes the stream. Change the task to use `INSERT INTO ... SELECT`.

### Task never runs
- Verify the task is resumed: `SHOW TASKS ...` should show `state = 'started'`
- Verify the stream has data: `SELECT * FROM <stream>`
- Check task history for errors (Step 6.2 above)

### Service function returns error
- **404 Not found**: No public workflow with that name exists in controld. Verify the workflow is deployed and set to Public visibility.
- **401 Unauthorized**: If using bearer token auth (external function), the header doesn't match `SNOWFLAKE_WEBHOOK_SECRET`.
- **Timeout**: The workflow takes too long. Use `?mode=async` or increase `BATCH_TIMEOUT_SECS` on the service function.

### Workflow runs but doesn't receive params
- Verify the `OBJECT_CONSTRUCT` column names match what the workflow expects (case-sensitive).
- All values must be cast to `::VARCHAR` since params are string key-value pairs.
- The workflow manifest must declare params in both `params:` (top-level) and `config[].parameters` (for runtime delivery to `sdk.getParameters()`).

### Stream not capturing rows
- Verify the stream is on the correct table: `SHOW STREAMS ...`
- If using `APPEND_ONLY = TRUE`, only INSERTs are captured (not updates or deletes)

## Security Considerations

| Layer | What it controls |
|-------|-----------------|
| Snowflake function USAGE grant | Who can call the service function |
| SPCS service role | Which roles can reach the webhook endpoint |
| Workflow visibility (Public) | Which workflows the webhook can trigger |
| SPCS ingress OAuth | Network-level access to the controld service |
| Bearer token (optional) | Extra HTTP-level auth for external callers |

Only grant function USAGE to the roles that need it. The task owner role needs USAGE on the function and the service role grant.

## Complete Example (SPCS Service Function)

For a `USERS` table triggering a `NEW_USER` workflow on SPCS:

```sql
-- 1. Stream
CREATE OR REPLACE STREAM MYDB.PUBLIC.USERS_STREAM
    ON TABLE MYDB.PUBLIC.USERS
    APPEND_ONLY = TRUE;

-- 2. Service Function
CREATE OR REPLACE FUNCTION MYDB.PUBLIC.trigger_new_user_workflow(row_data VARIANT)
    RETURNS VARIANT
    SERVICE = P67.APP.CONTROLD
    ENDPOINT = web
    AS '/api/webhook/snowflake/NEW_USER';

GRANT USAGE ON FUNCTION MYDB.PUBLIC.trigger_new_user_workflow(VARIANT)
    TO ROLE MY_APP_ROLE;

-- 3. Log Table
CREATE TABLE IF NOT EXISTS MYDB.PUBLIC.WEBHOOK_LOG (
    TRIGGERED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    USER_ID VARCHAR,
    USER_NAME VARCHAR,
    USER_EMAIL VARCHAR,
    RESULT VARIANT
);

-- 4. Task (must be INSERT INTO to consume the stream!)
CREATE OR REPLACE TASK MYDB.PUBLIC.PROCESS_NEW_USERS
    WAREHOUSE = COMPUTE_WH
    SCHEDULE = '1 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('MYDB.PUBLIC.USERS_STREAM')
AS
    INSERT INTO MYDB.PUBLIC.WEBHOOK_LOG (USER_ID, USER_NAME, USER_EMAIL, RESULT)
    SELECT
        ID::VARCHAR,
        NAME,
        EMAIL,
        MYDB.PUBLIC.trigger_new_user_workflow(
            OBJECT_CONSTRUCT('ID', ID::VARCHAR, 'NAME', NAME, 'EMAIL', EMAIL)
        )
    FROM MYDB.PUBLIC.USERS_STREAM
    WHERE METADATA$ACTION = 'INSERT';

-- 5. Resume
ALTER TASK MYDB.PUBLIC.PROCESS_NEW_USERS RESUME;

-- 6. Test
INSERT INTO MYDB.PUBLIC.USERS (NAME, EMAIL) VALUES ('Test User', 'test@example.com');

-- 7. Check results (after ~1 minute)
SELECT * FROM MYDB.PUBLIC.WEBHOOK_LOG ORDER BY TRIGGERED_AT DESC LIMIT 5;
```

## External Function Alternative

When controld runs outside SPCS (local Docker, external cloud), use an external function with an API integration:

```sql
-- API Integration
CREATE OR REPLACE API INTEGRATION p67_webhook_integration
    API_PROVIDER = SNOWFLAKE_INGRESS
    API_ALLOWED_PREFIXES = ('https://my-controld.snowflakecomputing.app')
    ENABLED = TRUE;

-- External Function (with bearer token auth)
CREATE OR REPLACE EXTERNAL FUNCTION MYDB.PUBLIC.trigger_new_user_workflow(row_data VARIANT)
    RETURNS VARIANT
    API_INTEGRATION = p67_webhook_integration
    HEADERS = ('Authorization' = 'Bearer my-secret-token')
    AS 'https://my-controld.snowflakecomputing.app/api/webhook/snowflake/NEW_USER';
```

The rest of the setup (stream, task, log table) is identical. The only difference is how the function is created.
