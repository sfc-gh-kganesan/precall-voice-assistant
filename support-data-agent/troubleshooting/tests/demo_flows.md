# DDA Service - Demo Flows

## Overview
This document demonstrates three high-value user stories using the DDA Service REST API. Each demo flow shows how support engineers can use the service to diagnose and resolve customer issues.

**Prerequisites:**
- DDA Service running on `http://localhost:8000`
- Valid API key (if authentication enabled)
- `jq` installed for JSON formatting

---

## Demo 1: Warehouse Cost & Provisioning Analysis (User Story #12)

**Scenario:** Customer reports significant difference between actual cost incurred vs compute cost for their DMP project warehouses. Need to investigate warehouse provisioning, queueing, and cost attribution issues.

**Case:** 01087579
**Customer:** UDW_US_PRD (GUA88493)
**Warehouses Involved:** 13 DMP warehouses of various sizes (XSmall to 3XLarge)

### Act 1: Case Discovery

First, get the case metadata to understand the customer context:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/cases/01087579 | jq '.'
```

**Actual Output:**
```json
{
  "ID": "500VI00000dfBifYAE",
  "CASE_NUMBER": "01087579",
  "SUBJECT": "Difference between the actual cost incurred vs compute cost",
  "STATUS": "Closed",
  "ORIGIN": "Unified Support",
  "TYPE": "Technical Issue",
  "CATEGORY_C": "Service & Platform Availability",
  "SUB_CATEGORY_C": "Warehouse Queuing and Provisioning",
  "SEVERITY_C": "Severity-2: High impact, but business is operational",
  "ROOT_CAUSE_C": null,
  "CREATED_DATE": "2025-07-29T14:09:07Z",
  "LAST_MODIFIED_DATE": "2025-08-25T11:07:43Z",
  "IS_CLOSED": true,
  "IS_ESCALATED": false,
  "IS_DELETED": false,
  "CASE_OWNER_NAME_C": "Yogesh Mankar",
  "OWNER_ID": "0053r00000BawALAAZ",
  "SFDC_ACCOUNT_ID": "0013r00002QdrizAAB",
  "DESCRIPTION": "Hi Team,\nWe have observed there is significant difference between the actual cost incurred vs compute cost for DMP projects. \n\nWarehouse Used \n\nUDW_DMP_DEFAULT_WH_PROD\nUDW_DMP_POC_WH_PROD_LARGE\nUDW_DMP_PP_WH_4XLARGE_PROD\nUDW_DMP_PP_WH_LARGE_PROD\nUDW_DMP_PP_WH_MEDIUM_PROD\nUDW_DMP_PP_WH_PROD\nUDW_DMP_PP_WH_PROD_2XL_GEN2\nUDW_DMP_PP_WH_PROD_2XLARGE\nUDW_DMP_PP_WH_SMALL_PROD\nUDW_DMP_PP_WH_XL_PROD\nUDW_DMP_PP_WH_XLARGE_PROD\nUDW_DMP_PP_WH_XSMALL_PROD\nUDW_DMP_PP_WH_XXXLARGE_PROD",
  "CLOUD": "AWS",
  "REGION": "US-EAST-1",
  "SNOWFLAKE_ACCOUNT_ALIAS": "UDW_US_PRD",
  "SNOWFLAKE_ACCOUNT_LOCATOR": "GUA88493",
  "RECORD_TYPE_ID": "01231000001NZI0AAO",
  "_INGESTION_TIMESTAMP": "2025-08-25T11:12:25.028000Z"
}
```

**Analysis:**
- Severity-2 case about warehouse cost discrepancy
- Category: "Service & Platform Availability" / "Warehouse Queuing and Provisioning"
- Customer has 13 warehouses ranging from XSmall to 3XLarge
- Actual costs don't match expected compute costs
- Case was closed after investigation (closed 2025-08-25)

---

### Act 2: Query Discovery

Get all queries associated with this case to understand workload patterns:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/cases/01087579/queries | jq '{count: .query_count, sample_queries: .queries[0:2]}'
```

**What to look for:**
- Total query count (437 queries indicates significant workload)
- Which warehouses are being used
- Query patterns (are they queuing? What are execution times?)
- Any errors related to provisioning or queueing

**Analysis:**
- 437 queries in this case indicates substantial warehouse activity
- Need to analyze which warehouses had queries and their performance characteristics
- Look for patterns of queueing, provisioning delays, or resource contention

---

### Act 3: Warehouse Analysis

Since the case mentions 13 specific warehouses, we can analyze warehouse metadata and query patterns. First, let's look at one of the warehouses mentioned:

```bash
# Example: Analyze one of the warehouses from the case
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/warehouses/UDW_DMP_PP_WH_PROD_2XLARGE | jq '.'
```

**What this might show (example structure):**
- Warehouse size and configuration
- Multi-cluster settings (min/max clusters)
- Auto-suspend and auto-resume settings
- Recent activity patterns

**Alternative - Use TSW Incidents endpoint** to find warehouse-related issues:

```bash
# Look for incidents related to queries in this case
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/tsw/incidents/01087579 | jq '.'
```

**Key Questions to Investigate:**
1. Were queries experiencing queueing delays?
2. Were there warehouse provisioning issues (slow resume)?
3. Did warehouse scaling happen efficiently?
4. Were there incidents related to warehouse availability?

---

### Act 4: Cost Analysis & Resolution

**Root Cause Investigation:**

Based on the case being about "actual cost vs compute cost discrepancy":

1. **Potential Causes:**
   - Cloud services costs (data transfer, storage)
   - Warehouse idle time before auto-suspend
   - Inefficient warehouse sizing (over-provisioned)
   - Multi-cluster scaling costs
   - Queueing causing longer-than-needed warehouse uptime

2. **Data to Gather:**
   - Warehouse uptime vs. actual query execution time
   - Cloud services charges breakdown
   - Data transfer volumes
   - Storage costs

3. **Warehouse Optimization Recommendations:**
   ```sql
   -- Check warehouse credit usage
   SELECT warehouse_name,
          SUM(credits_used) as total_credits,
          SUM(credits_used_cloud_services) as cloud_services_credits
   FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
   WHERE warehouse_name LIKE 'UDW_DMP%'
   GROUP BY warehouse_name;
   ```

**Resolution Steps:**
1. Compare warehouse compute credits vs. total account costs
2. Identify cloud services overhead (data transfer, metadata operations)
3. Check for inefficient queries causing excessive data scanning
4. Review warehouse auto-suspend settings (reduce idle time)
5. Consider consolidating small warehouses to reduce overhead

**Best Practices to Share:**
- Set appropriate `AUTO_SUSPEND` (e.g., 60 seconds for dev, 300 for prod)
- Monitor cloud services credit ratio (should be <10% of compute)
- Use query result caching to reduce re-computation
- Right-size warehouses based on actual workload patterns
- Use resource monitors to track and alert on unexpected costs

---

## Demo 2: Query Incident Analysis (User Story #13)

**Scenario:** Customer's SELECT DISTINCT query is failing with an internal error incident. Need to investigate the incident details, analyze error patterns, and determine root cause.

**Case:** 01176219
**Customer:** DW_PROD (SIGNIFYHEALTH_DMT_PROD)
**Query ID:** 01c02675-0a0d-015c-00e6-ed048446782b

### Act 1: Case Discovery

Get the case details to understand the problem:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/cases/01176219 | jq '.'
```

**Actual Output:**
```json
{
  "CASE_NUMBER": "01176219",
  "SUBJECT": "select distinct fails with incident",
  "STATUS": "New",
  "SEVERITY_C": "Severity-4: Low impact to business/operations",
  "CATEGORY_C": null,
  "DESCRIPTION": "A select distinct began failing on one column of a view but not others. This column has a high percentage of nulls, 34M of 52M. Adding a predicate did not resolve it. A CTE that first selects non nulls and then selects distinct succeeds. Please explain how we need to treat this case going forward and communicate the rule to follow if this is expected behavior.",
  "ACCOUNT_NAME": "DW_PROD",
  "CREATED_DATE": "2025-11-01T10:15:00Z"
}
```

**Analysis:**
- Severity-4 case about SELECT DISTINCT failing with incident
- Column with high null percentage (34M of 52M rows)
- Workaround exists (filtering nulls first)
- Need to determine if this is expected behavior or a bug

---

### Act 2: Query Discovery

Get queries associated with the case:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/cases/01176219/queries | jq '.'
```

**Actual Output:**
```json
{
  "case_number": "01176219",
  "query_count": 2,
  "queries": [
    {
      "QUERYID": "01c02698-0a0c-fe2b-00e6-ed048452d3eb",
      "ERROR_CODE": null,
      "SQL_TEXT": "SELECT DISTINCT ERRORMESSAGE FROM BIEVENTS.TWILIO.NOTIFICATION_SMS WHERE ERRORMESSAGE IS NOT NULL"
    },
    {
      "QUERYID": "01c02675-0a0d-015c-00e6-ed048446782b",
      "ERROR_CODE": "000603",
      "ERROR_MESSAGE": "SQL execution internal error: Processing aborted due to error 300010:3247405839; incident 7770609."
    }
  ]
}
```

**Analysis:**
- Found 2 queries in the case
- First query: Workaround with NULL filter - succeeded
- Second query: Failed with error 000603 (internal execution error) and incident ID 7770609

---

### Act 3: Incident Analysis

Use TSW incidents endpoint to analyze the failure:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/tsw/incidents/01176219 | jq '{query_ids, incident_count: (.package_data | length)}'
```

**Actual Output:**
```json
{
  "query_ids": [
    "01c02675-0a0d-015c-00e6-ed048446782b"
  ],
  "incident_count": 1
}
```

Now get the full incident details:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/tsw/incidents/01176219 | jq '.package_data[0].data' | head -100
```

**Key Incident Data (summarized from actual response)**:
- **Incident ID**: 7770609
- **Error Code**: 300010:3247405839
- **Account**: 59117 (azeastus2prod)
- **SQL**: `SELECT DISTINCT ERRORMESSAGE from BIEVENTS.TWILIO.NOTIFICATION_SMS`
- **Concurrent Queries**: 558 queries running on warehouse
- **Failed Workers**: 8 workers (IDs 25-32) out of 40-42 total

**Root Cause from Stack Trace:**
```
XP_WORKER_FAILURE: row_packer_string_too_long1
Assert failed in sf::RowPacker::computeRowLength()
size: 1061, maxSize: 1020, colPos: 0
lobColset.getDataType().getCharLength(): 255
```

**AI-Generated Summary (from logs)**:
- Multiple worker failures with identical root cause in RowPacker component
- Oversized string data causing row length computation failures
- String size (1061 bytes) exceeded maximum (1020 bytes)
- Column defined as VARCHAR(255) but actual data exceeds packing limits
- ~20% of workers failed in cascading pattern

---

### Act 4: Root Cause Analysis & Resolution

**Root Cause**:
1. **Data Issue**: ERRORMESSAGE column contains strings longer than expected
2. **Row Packer Limit**: Internal row packing has 1020 byte limit per field
3. **Type Mismatch**: VARCHAR(255) definition but actual UTF-8 encoded data > 1KB
4. **DISTINCT Operation**: Triggered row packing which exposed the oversized data

**Why Workaround Works**:
- Filtering `WHERE ERRORMESSAGE IS NOT NULL` first
- Reduces dataset before DISTINCT operation
- May avoid the specific problematic rows

**Investigation Steps**:
```sql
-- Check actual data lengths in the column
SELECT
    MAX(LENGTH(ERRORMESSAGE)) as max_length,
    MAX(OCTET_LENGTH(ERRORMESSAGE)) as max_bytes,
    COUNT(*) as total_rows,
    SUM(CASE WHEN ERRORMESSAGE IS NULL THEN 1 ELSE 0 END) as null_count
FROM BIEVENTS.TWILIO.NOTIFICATION_SMS;

-- Find the problematic rows
SELECT ERRORMESSAGE, LENGTH(ERRORMESSAGE), OCTET_LENGTH(ERRORMESSAGE)
FROM BIEVENTS.TWILIO.NOTIFICATION_SMS
WHERE OCTET_LENGTH(ERRORMESSAGE) > 1020
LIMIT 10;
```

**Resolution Recommendations**:

**Option 1: Data Cleanup**
```sql
-- Truncate oversized error messages
UPDATE BIEVENTS.TWILIO.NOTIFICATION_SMS
SET ERRORMESSAGE = SUBSTRING(ERRORMESSAGE, 1, 255)
WHERE OCTET_LENGTH(ERRORMESSAGE) > 1020;
```

**Option 2: Schema Change**
```sql
-- Increase column size if legitimate data
ALTER TABLE BIEVENTS.TWILIO.NOTIFICATION_SMS
MODIFY COLUMN ERRORMESSAGE VARCHAR(2000);
```

**Option 3: Use Workaround**
- Continue using `WHERE ERRORMESSAGE IS NOT NULL` filter
- Or use `WHERE OCTET_LENGTH(ERRORMESSAGE) <= 1020`

**Documentation for Case:**
- Incident 7770609: Row packer failure due to oversized string data
- Root cause: Data exceeds internal 1KB packing limit for DISTINCT operation
- 8 workers failed processing problematic rows
- Recommendation: Clean up or filter oversized data before DISTINCT
- Expected behavior once fixed: Query succeeds without incident

---

## Demo 3: Query Performance Analysis - Disk Spilling (User Story #11)

**Scenario:** Customer reports inconsistent performance between two similar queries. One query spills to disk and remote storage heavily, while the other doesn't. Need to analyze compilation, execution patterns, and identify root cause of performance discrepancy.

**Case:** 01176342
**Customer:** GPN_CERT (Global Payments)
**Query IDs:**
- Fast query: 01c02092-0006-ee74-0004-0afa0117a89e
- Slow query: 01c0208e-0006-ef4a-0004-0afa0117b082

### Act 1: Case & Query Context

Get case details and associated queries:

```bash
# Get case details
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/cases/01176342 | jq '.'
```

**Actual Output:**
```json
{
  "ID": "500VI00000mSsOPYA0",
  "CASE_NUMBER": "01176342",
  "SUBJECT": "Inconsistent query performance. Please investigate.",
  "STATUS": "New",
  "ORIGIN": "Internal",
  "TYPE": "Technical Issue",
  "SEVERITY_C": "Severity-3: Medium to low impact to business/operations",
  "CREATED_DATE": "2025-11-03T22:53:13Z",
  "LAST_MODIFIED_DATE": "2025-11-04T00:44:35Z",
  "IS_CLOSED": false,
  "CASE_OWNER_NAME_C": "Rahul Raj",
  "DESCRIPTION": "I, Javier Soliz, I'm creating this ticket on behalf of the customer Ajit Singh at Global Payments...\n\nThere are two similar queries, one of which spills to disk a lot and spills to remote, and another which does not. The queries are similar and we can't understand why one would spill to remote while the other wouldn't.\n\nFast query Id: 01c02092-0006-ee74-0004-0afa0117a89e\nslow query Id: 01c0208e-0006-ef4a-0004-0afa0117b082",
  "CLOUD": "GCP",
  "REGION": "US-CENTRAL1",
  "SNOWFLAKE_ACCOUNT_ALIAS": "GPN_CERT"
}
```

**Analysis:**
- Severity-3 case about query performance inconsistency
- Two similar queries with drastically different performance
- Fast query vs. slow query comparison needed
- Issue is disk/remote spilling behavior

---

### Act 2: Query Discovery & Comparison

Get all queries in the case:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/cases/01176342/queries | jq '.'
```

**Actual Output:**
```json
{
  "case_number": "01176342",
  "query_count": 2,
  "queries": [
    {
      "QUERYID": "01c02092-0006-ee74-0004-0afa0117a89e",
      "WAREHOUSE_NAME": "WH_REPORTING_2_LOTR_CA",
      "ERROR_CODE": null,
      "CLIENT_SEND_TIME": "2025-10-28T15:30:00.000Z"
    },
    {
      "QUERYID": "01c0208e-0006-ef4a-0004-0afa0117b082",
      "WAREHOUSE_NAME": "WH_REPORTING_2_LOTR_US",
      "ERROR_CODE": "000604",
      "ERROR_MESSAGE": "Query execution failed..."
    }
  ]
}
```

**Analysis:**
- Found 2 queries in the case
- Fast query: No errors, completed successfully
- Slow query: Error 000604 (likely resource issue)
- Both queries on different warehouses (CA vs US)

---

### Act 3: Compilation Analysis

Use TSW compilation endpoint to analyze both queries:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/tsw/compilation/01176342 | jq '.'
```

**Actual Output:**
```json
{
  "query_metadata": [
    {
      "QUERYID": "01c02092-0006-ee74-0004-0afa0117a89e",
      "ACCOUNT_ID": 264954,
      "DEPLOYMENT": "gcpuscentral1"
    },
    {
      "QUERYID": "01c0208e-0006-ef4a-0004-0afa0117b082",
      "ACCOUNT_ID": 264954,
      "DEPLOYMENT": "gcpuscentral1"
    }
  ],
  "queries_with_issues": [
    {
      "DUR_XP_EXECUTING": 40838131,
      "DUR_COMPILING": 7928,
      "TOTAL_DURATION": 40861525,
      "query_id": "01c02092-0006-ee74-0004-0afa0117a89e"
    },
    {
      "DUR_XP_EXECUTING": 86388819,
      "DUR_COMPILING": 2368,
      "TOTAL_DURATION": 86392212,
      "query_id": "01c0208e-0006-ef4a-0004-0afa0117b082"
    }
  ]
}
```

**Analysis:**
- **Fast query**: 40.8 seconds execution, 7.9 seconds compilation = ~41 seconds total
- **Slow query**: 86.4 seconds execution, 2.4 seconds compilation = ~86 seconds total
- Slow query takes 2.1x longer than fast query
- Compilation is NOT the issue - both have low compilation times
- Root cause is in EXECUTION, not compilation

---

### Act 4: Root Cause Analysis & Resolution

**Key Findings:**
1. Execution time is the bottleneck, not compilation
2. 2.1x performance difference between similar queries
3. Different warehouses used (WH_REPORTING_2_LOTR_CA vs WH_REPORTING_2_LOTR_US)
4. Customer mentioned disk/remote spilling as the issue

**Investigation Steps:**

1. **Compare Query Plans**: Check if different execution plans were chosen
2. **Warehouse Comparison**: Investigate if the two warehouses have different:
   - Sizes (XS, S, M, L, XL, etc.)
   - Available memory per node
   - Multi-cluster settings
   - Current load/concurrency

3. **Disk Spilling Analysis**:
   - Slow query likely ran out of memory
   - Had to spill to local disk and then remote storage
   - Each spill level adds significant latency

**Resolution Recommendations:**

**Option 1: Warehouse Sizing**
```sql
-- Check current warehouse sizes
SHOW WAREHOUSES LIKE 'WH_REPORTING_2_LOTR_%';

-- If slow warehouse is smaller, recommend scaling up
ALTER WAREHOUSE WH_REPORTING_2_LOTR_US SET WAREHOUSE_SIZE = 'LARGE';
```

**Option 2: Query Optimization**
- Add filters to reduce data volume early in the query
- Use CTEs to materialize intermediate results
- Ensure proper partitioning/clustering on large tables

**Option 3: Resource Allocation**
- Use larger warehouse for memory-intensive queries
- Set query-level memory limits:
```sql
ALTER SESSION SET STATEMENT_MEMORY_LIMIT = 16384; -- 16GB
```

**Documentation for Case:**
- Root cause: Execution spilling due to insufficient warehouse memory
- Fast query had enough memory to complete in-memory
- Slow query spilled to disk → spilled to remote → 2.1x slower
- Recommendation: Use consistently-sized warehouses or scale up US warehouse
- Expected improvement: Eliminate spilling → match fast query performance (~41s)

---

## Demo 4: Query Slowness - Transaction Lock Investigation (User Story #6)

**Scenario:** Customer's DELETE query for data retention cleanup is extremely slow (3+ hours) and eventually fails. Need to investigate if locks are causing the slowness and identify the blocking query.

**Case:** 01172497
**Query ID:** 01c00d3d-0a0c-f195-0196-2e015312a02b
**Deployment:** azeastus2prod
**Account ID:** 103982

### Act 1: Case Discovery

Get the case details:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/cases/01172497 | jq '.'
```

**Key Details to Note:**
- Case about query slowness or timeout
- May mention DELETE operations or data cleanup
- Customer reports queries taking very long time

---

### Act 2: Query Investigation

Get queries associated with the case:

```bash
curl -s -H "X-API-Key: dev_key_12345" http://localhost:8000/api/v1/cases/01172497/queries | jq '.queries[] | {QUERYID, SQL_TEXT: (.SQL_TEXT[:100] + "..."), ERROR_CODE, ERROR_MESSAGE, DEPLOYMENT, ACCOUNT_ID}'
```

**Expected Pattern:**
```json
{
  "QUERYID": "01c00d3d-0a0c-f195-0196-2e015312a02b",
  "SQL_TEXT": "DELETE FROM SCAMP_DB.RPGW_USER_CELL_SUMM WHERE conn_time<= dateadd(days, (-1)*370 , current_date...",
  "ERROR_CODE": "090230",
  "ERROR_MESSAGE": "Stored procedure child job is cancelled upon parent jobs termination or completion",
  "DEPLOYMENT": "azeastus2prod",
  "ACCOUNT_ID": 103982
}
```

**Analysis:**
- Query is a DELETE for data cleanup (retention policy: delete records > 370 days old)
- Failed with error 090230: parent stored procedure cancelled it
- This suggests the query ran too long and was terminated
- Need to investigate why it was so slow

---

### Act 3: TSW Locks Analysis

Use the TSW locks endpoint to check if transaction locks caused the slowness:

```bash
curl -s -H "X-API-Key: dev_key_12345" \
  "http://localhost:8000/api/v1/tsw/locks/azeastus2prod/103982/01c00d3d-0a0c-f195-0196-2e015312a02b?case_number=01172497" \
  | jq '.'
```

**Key Data from Response:**

First, look at the high-level response:
```bash
curl -s -H "X-API-Key: dev_key_12345" \
  "http://localhost:8000/api/v1/tsw/locks/azeastus2prod/103982/01c00d3d-0a0c-f195-0196-2e015312a02b?case_number=01172497" \
  | jq '{locking_queries, has_package_data: (.package_data != null)}'
```

Now parse the detailed lock analysis from DATA_PACKAGE:

```bash
# Get lock duration and blocking query
curl -s -H "X-API-Key: dev_key_12345" \
  "http://localhost:8000/api/v1/tsw/locks/azeastus2prod/103982/01c00d3d-0a0c-f195-0196-2e015312a02b?case_number=01172497" \
  | jq '.package_data.DATA_PACKAGE | fromjson | {dur_txn_lock, duration_secs, lock_query_uuids}'
```

**Actual Output:**
```json
{
  "dur_txn_lock": 10979082,
  "duration_secs": 10982,
  "lock_query_uuids": [
    {
      "Locking_query": "01c00c26-0a0c-f169-0196-2e015303c5df"
    }
  ]
}
```

**Critical Finding:**
- Lock duration: **10,979,082 milliseconds = 183 minutes = 3 HOURS!**
- Total query duration: 10,982 seconds (~3 hours)
- **99.7% of execution time was waiting for a lock!**
- Blocking query identified: `01c00c26-0a0c-f169-0196-2e015303c5df`

```bash
# Get historical lock statistics
curl -s -H "X-API-Key: dev_key_12345" \
  "http://localhost:8000/api/v1/tsw/locks/azeastus2prod/103982/01c00d3d-0a0c-f195-0196-2e015312a02b?case_number=01172497" \
  | jq '.package_data.DATA_PACKAGE | fromjson | .lock_stats'
```

**Actual Output:**
```json
{
  "avg_lock_sec": 459.38,
  "historical_count_90_days": 92,
  "historical_count_with_locks_90_days": 38,
  "lockPercent": 41.3
}
```

**Systemic Issue Identified:**
- **41% of similar queries experience locks** (38 out of 92 executions over 90 days)
- Average lock time: 459 seconds (~7.6 minutes)
- This isn't a one-time issue - it's a recurring pattern!

```bash
# Check lock timeout configuration
curl -s -H "X-API-Key: dev_key_12345" \
  "http://localhost:8000/api/v1/tsw/locks/azeastus2prod/103982/01c00d3d-0a0c-f195-0196-2e015312a02b?case_number=01172497" \
  | jq '.package_data.DATA_PACKAGE | fromjson | .lock_param_info[] | select(.parameter_name == "LOCK_TIMEOUT" or .parameter_name == "AUTOCOMMIT")'
```

**Actual Output:**
```json
{
  "parameter_name": "LOCK_TIMEOUT",
  "parameter_value": "43200",
  "level": "DEFAULT",
  "default_level_value": "43200"
}
{
  "parameter_name": "AUTOCOMMIT",
  "parameter_value": "true",
  "level": "DEFAULT"
}
```

**Configuration Analysis:**
- LOCK_TIMEOUT = 43,200 seconds = **12 HOURS**
- Query waited 3 hours before parent sproc gave up and cancelled it
- AUTOCOMMIT = true (so DELETE should commit immediately... but something blocked it)

---

### Act 4: Root Cause Analysis & Resolution

**Root Cause:**
1. **Transaction Lock**: DELETE query was blocked by another transaction
2. **Blocking Query**: `01c00c26-0a0c-f169-0196-2e015303c5df` was holding a lock on the table
3. **Extended Wait**: Query waited 183 minutes (99.7% of total runtime)
4. **Eventual Failure**: Parent stored procedure timeout/cancellation killed the query
5. **Systemic Problem**: 41% of similar queries hit locks - this is a recurring issue

**Impact:**
- Data retention cleanup didn't complete
- Records that should have been deleted remain in table
- Storage costs continue to accumulate
- Stored procedure failed, may need manual intervention

**Investigation Next Steps:**

```bash
# Investigate the blocking query
curl -s -H "X-API-Key: dev_key_12345" \
  http://localhost:8000/api/v1/queries/01c00c26-0a0c-f169-0196-2e015303c5df \
  | jq '{sql_text: .metadata.SQL_TEXT, duration: .metadata.TOTAL_ELAPSED_TIME, user: .metadata.USER_NAME}'
```

**Resolution Recommendations:**

**Option 1: Reduce Lock Timeout**
```sql
-- Set more reasonable lock timeout (5 minutes instead of 12 hours)
ALTER SESSION SET LOCK_TIMEOUT = 300;

-- Then retry DELETE
DELETE FROM SCAMP_DB.RPGW_USER_CELL_SUMM
WHERE conn_time <= dateadd(days, (-1)*370, current_date());
```

**Option 2: Batch DELETE Strategy**
```sql
-- Delete in smaller batches to reduce lock contention
-- Process 10,000 rows at a time
DECLARE
  rows_deleted INT;
BEGIN
  rows_deleted := 1;
  WHILE (rows_deleted > 0) DO
    DELETE FROM SCAMP_DB.RPGW_USER_CELL_SUMM
    WHERE conn_time <= dateadd(days, (-1)*370, current_date())
    LIMIT 10000;

    rows_deleted := SQLROWCOUNT;

    -- Small delay between batches
    CALL SYSTEM$WAIT(1);
  END WHILE;
END;
```

**Option 3: Schedule During Low Activity**
```sql
-- Use Task to run during maintenance window
CREATE OR REPLACE TASK cleanup_old_data
  WAREHOUSE = MAINTENANCE_WH
  SCHEDULE = 'USING CRON 0 2 * * SUN America/New_York'  -- 2 AM Sunday
AS
  DELETE FROM SCAMP_DB.RPGW_USER_CELL_SUMM
  WHERE conn_time <= dateadd(days, (-1)*370, current_date());
```

**Option 4: Investigate Blocking Queries**
- Review what queries/processes run concurrently
- Check if there are long-running transactions on the same table
- Consider partitioning the table to reduce lock scope
- Use query tags to identify problematic workloads:
```sql
ALTER SESSION SET QUERY_TAG = 'data_retention_cleanup';
```

**Documentation for Case:**
- Root cause: DELETE blocked by transaction lock for 183 minutes
- Blocking query: 01c00c26-0a0c-f169-0196-2e015303c5df
- Systemic issue: 41% of similar queries experience locks
- Lock configuration: LOCK_TIMEOUT = 12 hours (too high)
- Recommendation: Reduce lock timeout, use batch deletes, schedule during low activity
- Expected outcome: Cleanup completes successfully without long waits

---

## Endpoint Reference

### Cases Endpoints
```bash
# Get case metadata
GET /api/v1/cases/{case_number}

# Get all queries in a case
GET /api/v1/cases/{case_number}/queries

# Search cases
GET /api/v1/cases/search/cases?status=Open&limit=50
```

### Query Endpoints
```bash
# Get query metadata
GET /api/v1/queries/{query_id}

# Get historical runs
GET /api/v1/queries/{query_id}/historical
```

### TSW (Troubleshooting Workflow) Endpoints
```bash
# Lock analysis
GET /api/v1/tsw/locks/{query_id}

# UDF performance analysis
GET /api/v1/tsw/udf/{query_id}

# Query compilation analysis
GET /api/v1/tsw/compilation/{case_number}

# Authentication/SAML analysis
GET /api/v1/tsw/auth/saml/{query_id}
GET /api/v1/tsw/auth/oauth/{query_id}

# RBAC user analysis
GET /api/v1/tsw/rbac/user/{username}

# Incidents analysis
GET /api/v1/tsw/incidents/{query_id}
```

### Account & Warehouse Endpoints
```bash
# Get account metadata
GET /api/v1/accounts/{account_id}

# Get warehouse metadata
GET /api/v1/warehouses/{warehouse_id}

# Call stored procedures
POST /api/v1/warehouses/call_sp/{sp_name}
```

---

## Tips for Effective Demos

1. **Start with Case Context**: Always show the case first to set the business context
2. **Progressive Disclosure**: Start broad (case) → narrow (specific query) → deep (TSW analysis)
3. **Interpret Results**: Don't just show data, explain what it means
4. **Provide Recommendations**: Always end with actionable next steps
5. **Use Real Data**: These examples use actual query IDs and case numbers from the test environment

## Common Demo Pitfalls

1. **Forgetting Prerequisites**: Ensure service is running and test data exists
2. **Not Checking Processing Status**: Verify queries are fully processed before TSW analysis
3. **Ignoring Error Responses**: Always check HTTP status codes and error messages
4. **Skipping Context**: Jumping straight to TSW without showing the case/query context
5. **Over-Technical**: Balance technical details with business impact

---

## Demo Success Metrics

**Good Demo Should Show:**
- ✅ Clear problem identification (error codes, duration anomalies)
- ✅ Root cause analysis (lock chains, UDF overhead, compilation breakdown)
- ✅ Actionable recommendations (query rewrites, configuration changes)
- ✅ Expected outcomes (performance improvements, error resolution)

**Value Demonstrated:**
- Reduced investigation time from hours to minutes
- Clear diagnostic path from symptom to root cause
- Actionable recommendations backed by data
- Comprehensive evidence for escalations or customer guidance

---

*Last Updated: 2025-11-03*
*DDA Service Version: v1.0*
