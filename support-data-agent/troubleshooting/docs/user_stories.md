# DDA Application - End-to-End User Stories

## Overview
This document contains 15 comprehensive user stories demonstrating how support engineers use the DDA (Diagnostic Data Application) to diagnose and resolve customer issues with Snowflake.

---

## User Stories

### 1. Slow Query Investigation (Basic Query Analysis)
**Persona**: Support Engineer - Sarah
**Scenario**: Customer reports a specific query running slowly

1. **Landing Page**: Sarah logs into DDA and sees her recent activity and open cases on the landing page
2. **Search**: She enters the query ID from the case into the universal search bar
3. **Query Processing Status**: The app shows the query is 100% processed and ready for analysis
4. **Query Details Page**: She views comprehensive metadata:
   - Total duration: 45 seconds
   - Compilation: 2 seconds
   - Execution: 40 seconds
   - Queued overload: 3 seconds
5. **Duration Breakdown Chart**: Visual component shows most time spent in execution
6. **Historical Runs Tab**: She clicks to see this query ran 500+ times before, averaging 5 seconds
7. **Analysis**: Identifies this run as an anomaly - 9x slower than normal
8. **Concurrent Queries Tab**: Discovers 15 other queries running simultaneously in the same warehouse
9. **Warehouse Details**: Clicks through to see warehouse was undersized (Small) for the load
10. **Create JIRA**: Creates a ticket for SQL Pod with all evidence attached
11. **Case Update**: Returns to case to document findings and resolution

---

### 2. Account-Wide Performance Issues (Account View Analysis)
**Persona**: Support Engineer - Michael
**Scenario**: Customer reports all queries slow across their entire account

1. **Landing Page**: Michael opens DDA and sees the urgent case in his open cases list
2. **Search**: Enters the account name (e.g., "ACME_PROD") in search
3. **Account Page**: Loads account metadata showing:
   - Deployment: AWS US-WEST-2
   - Account type: CUSTOMER
   - Service level: BUSINESS CRITICAL
   - Current version: 7.32.5
4. **Release History Tab**: Checks when account was last upgraded (2 days ago)
5. **Account Queries Tab**: Filters to queries in last 2 days, sorts by duration
6. **Pattern Recognition**: Notices all slow queries have high "queued_provisioning_ms"
7. **Warehouses Tab**: Reviews all warehouses - sees auto-resume taking 30+ seconds
8. **Parameters Tab**: Checks account parameters for any recent changes
9. **Account Comparison**: Compares this account to a similar healthy account
10. **Root Cause**: Identifies warehouse resume delay after version upgrade
11. **Create JIRA**: Files bug report with Data Platform pod
12. **Case Resolution**: Documents workaround (disable auto-suspend temporarily)

---

### 3. Query Compilation Slowness (TSW Query Compilation Workflow)
**Persona**: Support Engineer - Priya
**Scenario**: Customer's query has abnormally high compilation time

1. **Case Page**: Priya opens case with query ID already linked
2. **Query Details**: Sees compilation time is 45 seconds (15% of execution time)
3. **TSW Selection**: Navigates to TSW (Troubleshooting Workflows) menu
4. **Query Compilation TSW**: Selects "Query Compilation" workflow
5. **Case Input**: Enters case number - app auto-discovers queries with high compilation
6. **Data Package Check**: System checks if TSW data package exists, loads cached analysis
7. **Compilation Breakdown**: Views detailed compilation stages:
   - Parsing: 2s
   - Optimization: 40s (anomaly!)
   - Code generation: 3s
8. **Plan Analysis**: Reviews query plan showing complex join with 20+ tables
9. **Recommendation**: System suggests query rewrite to reduce join complexity
10. **Evidence Collection**: Downloads compilation trace logs
11. **Create JIRA**: Files ticket with SQL pod including all TSW diagnostics
12. **Customer Guidance**: Provides query optimization recommendations to customer

---

### 4. Snowpipe Not Loading Data (Snowpipe Investigation)
**Persona**: Support Engineer - James
**Scenario**: Customer's Snowpipe stopped ingesting files

1. **Search**: James enters pipe name "DB.SCHEMA.CUSTOMER_EVENTS_PIPE"
2. **Snowpipe Page**: Loads pipe metadata showing:
   - Auto-ingest: Enabled
   - Status: INVALID
   - Error: "Stage not found"
3. **Pipe Definition**: Reviews CREATE PIPE statement showing stage path
4. **Metadata History**: Checks when pipe became invalid (2 hours ago)
5. **Status Timeline**: Views pipe status chart showing:
   - Pending files: 0
   - Active files: 0
   - Quarantined tasks: 150 (red flag!)
6. **Notification Integration**: Checks SQS queue configuration - looks correct
7. **Event Timeline**: Discovers stage was dropped and recreated
8. **Ingest Statistics**: Reviews recent copy history - no loads since stage recreation
9. **Root Cause**: Stage recreation changed internal stage ID, breaking pipe
10. **Resolution**: Instructs customer to recreate pipe pointing to new stage
11. **Validation**: Monitors status timeline to confirm ingestion resumes
12. **Case Documentation**: Updates case with resolution steps

---

### 5. Parameter Change Impact Analysis (Parameter View)
**Persona**: Support Engineer - Elena
**Scenario**: Customer asks about parameter change impact before applying BCR

1. **Landing Page**: Elena sees a parameter-related case assigned to her
2. **Search**: Searches for parameter "USE_CACHED_RESULT"
3. **Parameter Details Page**: Loads comprehensive parameter info:
   - Current default: TRUE
   - Parameter ID: 12345
   - Area: Query Execution
   - Component: Result Cache
   - Levels: SESSION, ACCOUNT
4. **Release History**: Shows parameter introduced in version 5.20.0
5. **BCR Tracking**: Sees slow rollout scheduled for next week (Week 45)
6. **Affected Accounts**: Views list of accounts in partial rollout
7. **Change Bundle**: Links to engineering JIRA for context
8. **Impact Analysis**: Reviews query performance data for accounts already on new value
9. **Account Check**: Verifies customer's account not in rollout yet
10. **Recommendation**: Advises customer to wait for rollout vs. setting manually
11. **Documentation**: Provides expected timeline and impact assessment
12. **Follow-up**: Sets reminder to check back after rollout completes

---

### 6. Transaction Lock Investigation (TSW Query Locks)
**Persona**: Support Engineer - David
**Scenario**: Query timed out with lock wait errors

1. **Query Details**: David opens query showing error "Transaction lock timeout"
2. **Duration Breakdown**: Sees "txn_lock_ms": 300,000 (5 minutes!)
3. **TSW Menu**: Selects "Query Locks" troubleshooting workflow
4. **Case Search**: Enters case number to find all queries with lock issues
5. **Lock Analysis Package**: Loads pre-computed lock chain analysis
6. **Lock Chain Visualization**: Shows:
   - Blocker query: Q1 (running 2 hours)
   - Waiter: Q2 (customer's query - waited 5 min, then timeout)
   - Resource: Table "CUSTOMERS"
7. **Blocker Details**: Clicks to investigate Q1:
   - Long-running UPDATE statement
   - No activity for 90 minutes (abandoned?)
   - Session still active
8. **Session Info**: Gets session ID and warehouse info for blocker
9. **Table Access Logs**: Reviews what operations were attempted
10. **Root Cause**: Identifies abandoned transaction holding locks
11. **Resolution**: Contacts customer to kill blocker session
12. **Validation**: Confirms customer's query succeeds on retry

---

### 7. UDF Performance Problem (TSW UDF Analysis)
**Persona**: Support Engineer - Rachel
**Scenario**: Query with Python UDF running extremely slow

1. **Query Page**: Rachel sees query duration 10 minutes, mostly in execution
2. **Query Text**: Reviews SQL showing Python UDF calls in SELECT
3. **TSW Selection**: Chooses "UDF Analysis" workflow
4. **UDF Metadata Extraction**: System calls stored procedure to extract UDF details
5. **UDF Summary**: Shows:
   - UDF name: PYTHON_PROCESS_JSON
   - Language: Python
   - Called: 1,000,000 times (once per row!)
   - Avg time per call: 600μs
6. **UDF Code Review**: Views function definition showing complex JSON parsing
7. **Performance Breakdown**:
   - UDF execution: 9 minutes
   - Rest of query: 1 minute
8. **Logs Analysis**: GS logs show constant UDF invocation overhead
9. **Recommendation**: Suggests vectorizing UDF or rewriting as native SQL
10. **Comparison**: Shows similar query without UDF runs in 30 seconds
11. **POC Query**: Provides rewritten query for customer to test
12. **Best Practices**: Documents UDF performance guidelines in case

---

### 8. Iceberg Table Issues (TSW Iceberg Analysis)
**Persona**: Support Engineer - Ahmed
**Scenario**: Customer experiencing problems with Iceberg table queries

1. **Case Page**: Ahmed reviews case mentioning "Iceberg table" in description
2. **TSW Menu**: Selects "Iceberg Table Analysis"
3. **Case Query Discovery**: System finds queries accessing Iceberg tables
4. **Query Selection**: Picks failing query from list
5. **Table Identification**: System extracts Iceberg table name from access logs
6. **Iceberg Data Package**: Loads cached analysis with:
   - Manifest file count: 50,000 (very high!)
   - Snapshot count: 5,000
   - Data file count: 500,000
   - Table format version: v1
7. **Metadata Analysis**: Shows excessive manifest files causing slow planning
8. **Maintenance History**: Checks when table was last optimized (never!)
9. **Recommendation**: Advises running OPTIMIZE and VACUUM commands
10. **Performance Comparison**: Shows planning time 45s vs. 2s for healthy tables
11. **Best Practices**: Provides Iceberg maintenance schedule
12. **Follow-up**: Customer runs optimization, confirms improvement

---

### 9. Authentication Failures (Account Security View)
**Persona**: Support Engineer - Sophia
**Scenario**: Customer reporting login failures

1. **Search**: Sophia enters account name from security case
2. **Account Page**: Navigates to "Security" tab
3. **Authentication Dashboard**: Shows:
   - Failed logins last 24h: 500
   - Successful logins: 2,000
   - Failure rate: 20% (abnormal!)
4. **Failure Analysis**: Views failure breakdown by:
   - Error type: "Invalid password" (90%)
   - User: Mostly one service account "ETL_SERVICE"
   - Time pattern: Every 5 minutes, consistent
5. **User Details**: Clicks on service account to see:
   - Password last rotated: 30 days ago
   - Using Snowflake auth (not SSO)
   - Locked status: Not locked
6. **Timeline Visualization**: Failures started exactly 30 days ago
7. **Root Cause**: Password expired, automated job using cached credential
8. **Recent Successful Logins**: Finds human logins to same account working fine
9. **Security Recommendation**: Advises switching service account to key-pair auth
10. **Case Resolution**: Customer rotates password, failures stop
11. **Follow-up**: Suggests implementing key-pair authentication

---

### 10. Adhoc Query Processing (Emergency Ingestion)
**Persona**: Support Engineer - Marcus
**Scenario**: Customer needs urgent analysis of query not in DDA yet

1. **Case Assignment**: Marcus gets urgent P1 case with query ID
2. **Search**: Enters query ID in search bar
3. **Not Found**: "Query not found in DDA" message appears
4. **Processing Status Check**: Sees query is 0% processed (not in pipeline yet)
5. **Adhoc Processing**: Clicks "Trigger Adhoc Processing" button
6. **Job Submission**: Enters:
   - Query ID: 01abc-def-123
   - Case number: 12345678
   - Priority: High
7. **Job Started**: System confirms adhoc pipeline triggered
8. **Progress Monitoring**: Refreshes status showing:
   - 10% - Query found in raw data
   - 50% - Historical stats computed
   - 75% - Warehouse stats computed
   - 100% - Complete!
9. **Analysis Available**: All tabs now populated with data
10. **Time Saved**: Analysis ready in 5 minutes vs. 24+ hour normal pipeline
11. **Investigation**: Proceeds with full query analysis
12. **Resolution**: Identifies and resolves issue within SLA

---

### 11. Query Comparison for Regression Testing
**Persona**: Support Engineer - Lisa
**Scenario**: Customer reports query slower after version upgrade

1. **Query Search**: Lisa finds the slow query (post-upgrade)
2. **Historical Runs**: Sees query has 1,000+ historical executions
3. **"Last Successful Run" Button**: Clicks to auto-find pre-upgrade execution
4. **Query Comparison**: Opens side-by-side comparison showing:
   - **Before**: 5 seconds, version 7.30.1
   - **After**: 45 seconds, version 7.32.0
5. **Duration Diff**:
   - Compilation: +2s (acceptable)
   - Execution: +38s (major regression!)
   - Queueing: Same
6. **Resource Diff**:
   - Bytes scanned: Same
   - Memory used: +200% (red flag!)
   - Partitions scanned: Same
7. **Plan Comparison**: Different SQL plan hash - optimizer changed
8. **Parameters Diff**: No parameter changes between runs
9. **Version Change**: Isolates issue to version upgrade
10. **Evidence Package**: Exports comparison with all details
11. **Create JIRA**: Files P0 bug report with SQL pod
12. **Workaround**: Suggests query hint to use old plan until fix deployed

---

### 12. Warehouse Sizing Recommendation
**Persona**: Support Engineer - Tom
**Scenario**: Customer asking if they need to resize warehouse

1. **Account Search**: Tom enters customer's account name
2. **Warehouses Tab**: Views list of all warehouses
3. **Warehouse Selection**: Clicks on "ANALYTICS_WH" (the one in question)
4. **Warehouse Details**: Shows current config:
   - Size: Medium
   - Min clusters: 1
   - Max clusters: 4
   - Scaling policy: Standard
5. **Load Charts** (last 7 days):
   - Query queue depth: Often >10 queries
   - Cluster utilization: 95%+ sustained
   - Spilling to disk: High
6. **Query Analysis**: Filters to queries on this warehouse
7. **Queueing Time**: Many queries showing 2-5 minute queue times
8. **Resource Statistics**: Queries spilling 100GB+ to local storage
9. **Performance Impact**: Calculates 30% of queries affected by queueing
10. **Sizing Recommendation**: Suggests upgrade to Large + increase min clusters to 2
11. **Cost Analysis**: Estimates cost increase vs. performance improvement
12. **Documentation**: Provides detailed sizing justification to customer

---

### 13. Incident Correlation (Query Incidents)
**Persona**: Support Engineer - Nina
**Scenario**: Multiple queries failing with crashes

1. **Query Details**: Nina investigates failed query with error code 1234
2. **Incidents Tab**: Clicks to see Crash Manager incidents
3. **Incident List**: Shows 3 incidents linked to this query:
   - Incident ID: INC-999888
   - Component: ExecutionEngine
   - Crash type: Segmentation fault
   - Occurrence count: 5
4. **Incident Details**: Links to full crash manager details
5. **Related Queries**: Clicks "View other affected queries"
6. **Pattern Analysis**: Discovers 50+ queries with same incident today
7. **Common Factors**:
   - Same version: 7.32.1
   - Same warehouse: Different
   - Same SQL pattern: Yes - all using window functions with large partitions
8. **Deployment Check**: Confirms incident only on AWS deployments
9. **Timeline**: All incidents started 6 hours ago (after deployment)
10. **Escalation**: Identifies as widespread incident, not customer-specific
11. **Create JIRA**: Files P0 incident report with SQL pod
12. **Incident Response**: Works with on-call engineer for emergency hotfix

---

### 14. Parent-Child Query Tree Analysis (Stored Procedure Debugging)
**Persona**: Support Engineer - Kevin
**Scenario**: Stored procedure failing, need to find which child query caused error

1. **Query Search**: Kevin enters parent query ID (the CALL statement)
2. **Query Details**: Shows stored procedure execution failed after 10 minutes
3. **Error Message**: Generic "Statement execution failed"
4. **Parent-Child Tree Tab**: Clicks to see execution tree
5. **Tree Visualization**: Shows hierarchical structure:
   - Parent: CALL MY_STORED_PROC (failed)
     - Child 1: CREATE TEMP TABLE (success, 1s)
     - Child 2: INSERT INTO TEMP (success, 5s)
     - Child 3: MERGE STATEMENT (FAILED, 9m)
     - Child 4-10: (not executed)
6. **Child 3 Investigation**: Clicks on failed MERGE query
7. **Error Details**: "Transaction lock timeout" after 9 minutes
8. **Root Cause**: Child query waiting on lock, caused whole procedure to fail
9. **SQL Review**: Examines MERGE statement for optimization opportunities
10. **Resolution**: Identifies problematic MERGE, suggests rewriting logic
11. **Testing**: Customer rewrites MERGE, stored procedure succeeds
12. **Documentation**: Updates case with detailed execution flow

---

### 15. RBAC User Permissions Issue (TSW RBAC User)
**Persona**: Support Engineer - Jennifer
**Scenario**: User cannot access certain tables despite having role

1. **Case Review**: Jennifer sees case about access denied error
2. **Query Details**: Query failed with "Insufficient privileges"
3. **TSW Menu**: Selects "RBAC User Analysis"
4. **User Search**: Enters username from query metadata
5. **User Overview**: Loads comprehensive RBAC analysis:
   - Active roles: 5 roles listed
   - Default role: ANALYST_ROLE
   - Query role: DATA_READER (different from default!)
6. **Role Hierarchy**: Visualizes role inheritance tree
7. **Granted Privileges**: Shows privileges for DATA_READER:
   - Database: READ (has access)
   - Schema: READ (has access)
   - Table: (MISSING - no table grants!)
8. **Expected vs. Actual**: Compares to similar working user
9. **Recent Changes**: Checks grant history - table grant revoked yesterday
10. **Root Cause**: Admin accidentally revoked grant during cleanup
11. **Evidence**: Exports privilege comparison report
12. **Resolution**: Customer re-grants SELECT privilege to role
13. **Validation**: User retries query successfully
14. **Prevention**: Suggests regular privilege audits

---

## Common Workflow Patterns

### Entry Points
1. **Landing Page** - Recent activity + Open cases
2. **Universal Search** - Query ID, Account, Case, Warehouse, Pipe, Parameter
3. **Case Page** - Pre-linked queries
4. **Direct Links** - Sent by customers or other systems

### Investigation Flow
1. **Initial Assessment** - Processing status, basic metadata
2. **Deep Dive** - Specific tabs/views based on problem type
3. **Context Gathering** - Historical data, comparisons, related entities
4. **Root Cause Analysis** - TSW workflows, specialized analysis
5. **Evidence Collection** - Charts, logs, comparisons, statistics

### Resolution Actions
1. **Create JIRA** - Escalate to engineering with evidence
2. **Customer Guidance** - Recommendations, workarounds, best practices
3. **Case Documentation** - Update case with findings
4. **Validation** - Confirm resolution worked
5. **Follow-up** - Monitor for recurrence

---

## Key Insights

### Most Common Workflows
- Query performance analysis (Stories 1, 3, 7, 11)
- Account-wide issues (Story 2)
- Data pipeline problems (Story 4)
- Security and access control (Stories 9, 15)

### Critical Features
- **Universal Search** - Used in almost every workflow
- **Query Processing Status** - Essential for determining data availability
- **Historical Comparison** - Key for identifying regressions
- **TSW Workflows** - Specialized deep-dive analysis tools
- **Cross-Entity Navigation** - Seamless movement between queries, accounts, warehouses, etc.

### Time Criticality
- **P1 Cases**: Need adhoc processing (5 min vs 24h) - Story 10
- **Performance Issues**: Historical comparison essential - Story 11
- **Incidents**: Pattern recognition across multiple queries - Story 13
- **Security Issues**: Timeline analysis critical - Story 9

### Integration Points
- **Crash Manager** - Incident correlation (Story 13)
- **JIRA** - Escalation to engineering pods (all stories)
- **Salesforce** - Case management integration (Story 2)
- **Analytics** - Usage tracking for recent activity (Story 10)

---

## Statistics Summary

- **Total User Stories**: 15
- **Views Covered**: 9 (Query, Account, Warehouse, Snowpipe, Parameter, Case, Landing Page, TSW, Account Security)
- **TSW Workflows**: 6 (Compilation, Locks, UDF, Iceberg, Incidents, RBAC User)
- **Average Steps per Workflow**: 11-12 steps
- **Key Decision Points**: Search, Tab Selection, TSW Selection, Evidence Collection, Resolution Action

---

*This document serves as a comprehensive reference for understanding how support engineers use the DDA application to diagnose and resolve complex Snowflake customer issues.*
