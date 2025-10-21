"""
Fake case generator for Snowflake support tickets.
"""
# ruff: noqa: E501

import random
from datetime import datetime, timedelta

TOPICS = [
    "Performance & Optimization",
    "Authentication & Access",
    "Data Loading & Ingestion",
    "Storage & Data Retention",
    "Configuration & Setup",
    "Security & Governance",
    "Query Optimization",
    "API & Integration",
    "Notebooks & ML",
    "Data Sharing & Marketplace",
    "Tasks & Orchestration",
    "Cortex AI & LLMs",
    "Snowpark & UDFs",
    "External Functions",
    "Cost & Billing",
    "Replication & DR",
    "Snowflake Horizon & Governance",
    "Unistore & Hybrid Tables",
    "Container Services & Kubernetes",
    "Git Integration & Version Control",
    "Snowflake Openflow",
    "Cross-Region & Cross-Cloud",
    "Event Tables & Logging",
    "Directory Tables & Unstructured Data",
    "Query Profile & Observability",
]

PRODUCTS_BY_CATEGORY = {
    "Data Platform": [
        "Query Performance",
        "Virtual Warehouses",
        "Snowpark-optimized Warehouses",
        "Query Acceleration Service",
        "Data Storage",
        "Materialized Views",
        "Views & Secure Views",
        "Semantic Views",
    ],
    "Data Engineering": [
        "Snowpipe",
        "Snowpipe Streaming",
        "Tasks & Streams",
        "Dynamic Tables",
        "External Tables",
        "Iceberg Tables",
        "Hybrid Tables",
        "Stages",
        "Snowflake Openflow",
    ],
    "Data Science & ML": [
        "Snowflake Notebooks",
        "Snowpark Python",
        "Snowpark ML",
        "Model Registry",
        "Feature Store",
        "ML Functions",
    ],
    "AI & Cortex": [
        "AI_COMPLETE",
        "AI_CLASSIFY",
        "AI_FILTER",
        "AI_AGG",
        "AI_EMBED",
        "AI_EXTRACT",
        "AI_SENTIMENT",
        "AI_SUMMARIZE_AGG",
        "Cortex Search",
        "Cortex Analyst",
        "Cortex Agents",
        "Cortex Fine-Tuning",
        "Cortex Knowledge Extensions",
        "Document AI",
        "Snowflake Intelligence",
    ],
    "Data Sharing": [
        "Secure Data Sharing",
        "Data Marketplace",
        "Private Data Exchange",
        "Listings",
        "Reader Accounts",
    ],
    "Security & Governance": [
        "Snowflake Horizon",
        "Row Access Policies",
        "Column Masking",
        "Tag-based Policies",
        "Object Tagging",
        "Audit Logs",
        "Network Policies",
        "Trust Center",
        "Tri-Secret Secure",
    ],
    "Developer Tools": [
        "Snowsight",
        "SnowSQL",
        "Snowflake CLI",
        "Python Connector",
        "JDBC Driver",
        "ODBC Driver",
        "VS Code Extension",
        "Streamlit",
        "Git Repositories",
        "Workspaces",
    ],
    "Administration": [
        "Account Management",
        "User Management",
        "Resource Monitors",
        "Replication",
        "Failover Groups",
        "Session Policies",
    ],
    "Advanced Features": [
        "Container Services",
        "Unistore",
        "Directory Tables",
        "Open Catalog",
        "Event Tables",
        "Native App Framework",
    ],
}

CASE_TEMPLATES = {
    "Performance & Optimization": [
        (
            "Query Acceleration Service not improving performance",
            "Enabled QAS on LARGE warehouse but queries still taking 45s. Query profile shows no acceleration applied. Eligible operators present but service not engaged.",
        ),
        (
            "Warehouse auto-suspend not working after WebSocket close",
            "Warehouse not auto-suspending after configured 5-minute timeout. WebSocket connection shows as closed in logs but warehouse remains ACTIVE.",
        ),
        (
            "Result cache bypass despite identical query",
            "Identical SELECT queries not hitting result cache. Checked query hash and parameters are identical. RESULT_SCAN returning empty.",
        ),
        (
            "Spilling to remote storage on X-LARGE warehouse",
            "Query profile showing 90% bytes spilled to remote storage even on X-LARGE warehouse. Local disk should be 256GB but spilling at 50GB.",
        ),
    ],
    "Notebooks & ML": [
        (
            "Notebook kernel OOM when training on 100M rows",
            "Snowflake Notebooks kernel crashing with OOM error during RandomForestClassifier training. Dataset is 100M rows, 50 columns. Using LARGE warehouse.",
        ),
        (
            "ML Functions FORECAST failing with insufficient data",
            "FORECAST function returning 'insufficient training data' error. Have 2 years of daily data (730 rows). Documentation says minimum is 2 periods.",
        ),
        (
            "Feature Store version retrieval returns None",
            "FeatureStore.retrieve_feature_values() returning None for specific version. Version exists in SHOW VERSIONS output. No error thrown.",
        ),
        (
            "Notebook Git sync failing with merge conflict",
            "Notebook auto-sync to Git repository failing. Error: 'merge conflict detected'. Cannot resolve in UI. Need CLI access to repository.",
        ),
    ],
    "Cortex AI & LLMs": [
        (
            "AI_COMPLETE timeout with claude-3-7-sonnet model",
            "SELECT AI_COMPLETE('claude-3-7-sonnet', prompt) timing out after 60s. Same query works with llama3.1-70b. Prompt is 2000 tokens.",
        ),
        (
            "AI_EMBED generating different vectors for same input",
            "AI_EMBED('snowflake-arctic-embed-l-v2.0', text) returning non-deterministic results. Same input text producing different embeddings across runs.",
        ),
        (
            "Cortex Fine-tuning job stuck at 0% progress",
            "Fine-tuning job for mistral-7b created 4 hours ago but still showing 0% progress. Status is RUNNING. Training dataset has 15K examples.",
        ),
        (
            "AI_CLASSIFY exceeding 500 category limit",
            "AI_CLASSIFY failing with 'too many categories' error. Passing 350 categories which is below documented 500 limit. Using llama3.1-405b model.",
        ),
        (
            "Provisioned throughput exhausted for AI_COMPLETE",
            "Getting rate limit errors on AI_COMPLETE despite provisioned throughput. Allocated 1M tokens/hour but hitting limit at 600K. No burst documented.",
        ),
        (
            "Cortex Search not returning relevant results",
            "Cortex Search index created successfully but queries returning irrelevant documents. Vector similarity scores all below 0.3. Re-indexing didn't help.",
        ),
        (
            "Document AI extraction failing on PDF forms",
            "Document AI failing to extract form fields from PDF. Works on text-based PDFs. Error: 'unsupported document structure'. File is valid PDF/A.",
        ),
    ],
    "Snowpark & UDFs": [
        (
            "Snowpark DataFrame.collect() hanging on 50GB result",
            "DataFrame.collect() hanging indefinitely on 50GB result set. Works fine with .limit(1000). Using Snowpark Python 1.20.0. No timeout error.",
        ),
        (
            "Python UDF memory limit exceeded at 512MB",
            "Python UDF failing with 'memory limit exceeded'. UDF processes JSON documents. Set IMPORTS_MEMORY=512MB. Individual docs are 10MB average.",
        ),
        (
            "Vectorized UDTF slower than non-vectorized",
            "Vectorized Python UDTF 5x slower than non-vectorized version. Processing 10M rows takes 2 hours. Expected performance improvement per docs.",
        ),
        (
            "Java UDF ClassNotFoundException in JAR",
            "Java UDF failing with ClassNotFoundException despite class in uploaded JAR. DESCRIBE FUNCTION shows JAR in imports. Works in local Maven build.",
        ),
        (
            "Snowpark pushdown not happening for filter",
            "DataFrame filter operation not being pushed down to Snowflake. Query profile shows full table scan. Filter is simple equality on indexed column.",
        ),
    ],
    "Data Sharing & Marketplace": [
        (
            "Marketplace listing not visible after 24 hours",
            "Published data listing to Marketplace 24 hours ago but still not visible in search. Status shows 'Published'. Metadata and preview data configured.",
        ),
        (
            "Secure share Time Travel not working for consumer",
            "Consumer cannot use Time Travel on shared table despite retention configured. Provider account has 7-day retention. Consumer getting 'not supported' error.",
        ),
        (
            "Private listing installation fails with privilege error",
            "Consumer installing private listing getting 'insufficient privileges' error. Consumer is ACCOUNTADMIN. Share includes USAGE on database and schema.",
        ),
        (
            "Reader account queries failing intermittently",
            "Reader account users experiencing intermittent 'session expired' errors. Sessions configured for 4 hours but expiring after 30 minutes.",
        ),
    ],
    "Tasks & Orchestration": [
        (
            "Task DAG child not triggering after parent",
            "Child task not executing after parent completes successfully. AFTER dependency configured. SHOW TASKS shows both enabled. Parent execution logged in task_history.",
        ),
        (
            "Stream missing INSERT operations",
            "Stream on table missing approximately 5% of INSERT operations. SHOW STREAMS shows stream is STALE=FALSE. Inserts visible in base table.",
        ),
        (
            "Serverless task failing with warehouse timeout",
            "Serverless task failing with 'warehouse timeout' error. Task doesn't specify warehouse. Compute resources should be auto-provisioned per docs.",
        ),
        (
            "Task graph execution skipping random tasks",
            "Task graph with 20 tasks randomly skipping 3-4 executions per run. No errors logged. Skipped tasks have no dependencies. FINALIZER always runs.",
        ),
    ],
    "Authentication & Access": [
        (
            "SAML SSO redirect loop after MFA enforcement",
            "Users stuck in redirect loop after MFA enforcement enabled. SAML assertion valid. Works with password auth. IdP is Okta with DUO MFA.",
        ),
        (
            "SCIM sync creating duplicate users daily",
            "SCIM provisioning from Azure AD creating duplicate users every sync. Email attribute matches but new users created. 50+ duplicates over 2 weeks.",
        ),
        (
            "OAuth refresh token expiring after 1 hour",
            "OAuth refresh tokens expiring after 1 hour despite REFRESH_TOKEN_VALIDITY_SECONDS=7776000. Client using snowflake-connector-python 3.12.0.",
        ),
        (
            "Key-pair authentication failing with valid keys",
            "Key-pair auth failing with 'invalid signature' error. Public key uploaded to user. Private key format validated. RSA 2048-bit PKCS#8 format.",
        ),
        (
            "Federated authentication timing out",
            "Users experiencing 30s timeout on federated authentication. Direct login works. Network policy allows IdP IPs. Issue started after account region change.",
        ),
    ],
    "Data Loading & Ingestion": [
        (
            "Snowpipe Streaming insertRows schema validation error",
            "Snowpipe Streaming insertRows failing with 'schema mismatch' error. Column types match table DDL. Using snowflake-ingest-java 2.3.0. Classic architecture.",
        ),
        (
            "COPY INTO failing with encoding despite UTF-8",
            "COPY INTO failing with 'invalid UTF-8 encoding' error. Files validated with file command show UTF-8. Tried FILE_FORMAT ENCODING='UTF-8'.",
        ),
        (
            "Snowpipe latency increased from 1min to 15min",
            "Snowpipe ingestion latency jumped from 60s to 15 minutes. No configuration changes. S3 event notifications arriving on time. 95th percentile 12 minutes.",
        ),
        (
            "Bulk load performance degraded 5x overnight",
            "COPY INTO performance dropped from 90 minutes to 8 hours for 1TB load. No schema changes. Same warehouse size (X-LARGE). Query profile shows clustering issues.",
        ),
        (
            "Snowpipe Streaming offset token not advancing",
            "getLatestCommittedOffsetToken returning same value despite successful inserts. New data visible in table. Channel status shows ACTIVE. High-performance architecture.",
        ),
    ],
    "Security & Governance": [
        (
            "Row access policy bypassed by ACCOUNTADMIN",
            "Row access policy not applying to ACCOUNTADMIN role. Documentation says ACCOUNTADMIN bypasses security. Need way to enforce policy for all users.",
        ),
        (
            "Dynamic masking showing unmasked PII in logs",
            "Masking policy applied but unmasked SSN visible in QUERY_HISTORY. Policy works in SELECT results. Snowsight query history shows plaintext.",
        ),
        (
            "Tag-based masking not auto-applying to new columns",
            "Created tag-based masking policy but not automatically applying to newly added columns with PII tag. Manual ALTER TABLE works. Docs say automatic.",
        ),
        (
            "Horizon Trust Center showing false positives",
            "Trust Center reporting 'HIGH' risk for tables without risk. All data is synthetic test data. Cannot dismiss alerts. Blocking compliance review.",
        ),
        (
            "Object tagging quota exceeded unexpectedly",
            "Hitting object tag quota (10K tags) with only 3K objects. Tag inheritance creating phantom tags. SHOW TAGS shows 9800 tags but cannot locate source.",
        ),
        (
            "Tri-Secret Secure key rotation failing",
            "Hybrid table key rotation failing with 'key verification error'. Customer-managed key in AWS KMS is valid. Rotation worked last month.",
        ),
    ],
    "Query Optimization": [
        (
            "Search Optimization Service not accelerating queries",
            "Search optimization enabled but queries not using SOS. Query plan shows SEARCH_INDEX_NOT_ACCESSED_NO_MATCH_FOUND. Maintenance budget increased to 100.",
        ),
        (
            "Clustering key not reducing partition scan",
            "Added clustering key on timestamp column but still scanning all partitions. SYSTEM$CLUSTERING_INFORMATION shows avg_depth 1.2 (excellent). Using BETWEEN filter.",
        ),
        (
            "Materialized view stuck in SUSPENDED_BY_ERROR",
            "Materialized view failing refresh with SUSPENDED_BY_ERROR state. Base table query works. Error log shows 'compilation error: unknown function'. MV created month ago.",
        ),
        (
            "Query rewrite not using materialized view",
            "Created MV to accelerate dashboard queries but query rewrite not engaging. MV definition matches query pattern. SHOW MATERIALIZED VIEWS shows BEHIND=FALSE.",
        ),
    ],
    "Storage & Data Retention": [
        (
            "Time Travel failing on Iceberg table",
            "SELECT FROM table AT(TIMESTAMP => ...) failing on Iceberg table. Error: 'Time Travel not supported'. Table uses Snowflake as catalog. Docs say supported.",
        ),
        (
            "Fail-safe storage charges for deleted tables",
            "Fail-safe billing shows charges for tables deleted 2 months ago. 7-day Fail-safe period should have expired. Storage costs are 10TB for deleted objects.",
        ),
        (
            "CLONE operation timing out on 5TB table",
            "CREATE TABLE clone AS CLONE OF source timing out after 2 hours. Zero-copy clone should be instant per docs. Table has 2 billion rows, 5TB data.",
        ),
        (
            "Time Travel showing wrong data version",
            "Time Travel query returning data from wrong timestamp. Queried version from 2 days ago shows data from yesterday. Query syntax validated.",
        ),
    ],
    "Cost & Billing": [
        (
            "Unexpected serverless compute charges",
            "Serverless compute costs 3x higher than expected. Only running Snowpipe and tasks. Expected $500/month, actual $1800. No workload changes.",
        ),
        (
            "Resource monitor not suspending warehouse",
            "Resource monitor configured to SUSPEND at 100 credits but warehouse still running at 180 credits consumed. Actions shows SUSPEND_IMMEDIATE. Notifications working.",
        ),
        (
            "Storage billing mismatch with table sizes",
            "Billing shows 50TB storage but TABLE_STORAGE_METRICS sum to 30TB. Queried TIME_TRAVEL_BYTES and FAILSAFE_BYTES - still 15TB gap. Cloud Services storage empty.",
        ),
        (
            "Cross-region data transfer costs unexpected",
            "TRANSFER_TYPE DATA_LAKE showing $5K charges. Iceberg tables in same region as account. EXTERNAL_VOLUME location verified. No cross-region replication.",
        ),
    ],
    "Replication & DR": [
        (
            "Replication lag increasing to 4 hours",
            "Database replication from us-west-2 to eu-central-1 lagging 4 hours. Was 15 minutes last week. No network policy changes. 500GB database.",
        ),
        (
            "Failover group missing objects after promotion",
            "Promoted secondary failover group but 15% of objects missing. SHOW REPLICATION DATABASES shows status REPLICATION_COMPLETE. Missing all UDFs and procedures.",
        ),
        (
            "Replication progress stuck at 60% for 10TB table",
            "Table replication stuck at 60% for 24 hours. SHOW REPLICATION PROGRESS shows same percentage. 10TB table, 8 billion rows. No errors in logs.",
        ),
        (
            "Account replication failing with privilege error",
            "Account replication setup failing with 'insufficient privileges on target account'. Source is ORGADMIN. Target account in same organization.",
        ),
    ],
    "Configuration & Setup": [
        (
            "Network policy blocking PrivateLink traffic",
            "Network policy configured with PrivateLink VPCE ID but connections still blocked. AWS PrivateLink endpoint is active. Getting 'IP not allowed' error.",
        ),
        (
            "Account parameter not propagating to sessions",
            "ALTER ACCOUNT SET STATEMENT_TIMEOUT_IN_SECONDS=300 not applying to new sessions. SHOW PARAMETERS shows 300 but sessions timing out at default 172800.",
        ),
        (
            "Private connectivity setup VPC endpoint timeout",
            "AWS PrivateLink endpoint created but connection times out. Service name verified. Security groups allow 443 inbound. Endpoint state is 'available'.",
        ),
        (
            "Multi-cluster warehouse not auto-scaling",
            "Multi-cluster warehouse configured with MIN=1 MAX=5 but staying at 1 cluster despite queue depth 30. Scaling policy is ECONOMY. Query load consistently high.",
        ),
    ],
    "API & Integration": [
        (
            "Python connector session expired after 4 hours",
            "snowflake-connector-python sessions expiring after 4 hours despite CLIENT_SESSION_KEEP_ALIVE=True. Application requires 24-hour sessions. Using v3.12.1.",
        ),
        (
            "JDBC driver PreparedStatement memory leak",
            "JDBC driver memory usage growing 100MB/hour. Memory profiler shows PreparedStatement objects not released. Application restart required every 8 hours.",
        ),
        (
            "REST API rate limiting at 100 req/min",
            "Getting HTTP 429 from Snowflake SQL API at 100 requests/minute. Documentation lists 100 req/sec limit. Using /api/v2/statements endpoint.",
        ),
        (
            "ODBC connection pool exhaustion",
            "ODBC application exhausting connection pool with 'too many connections' error. Pool configured for 100. Monitoring shows 40 active. Tableau Desktop 2024.1.",
        ),
    ],
    "Snowflake Horizon & Governance": [
        (
            "Data classification not detecting PII columns",
            "Horizon auto-classification not tagging columns with SSN/email patterns. Ran SYSTEM$CLASSIFY 2 days ago. Test table has SSN in column names.",
        ),
        (
            "Lineage graph missing downstream dependencies",
            "Object lineage in Horizon missing 40% of downstream views. Lineage tracked manually matches SHOW OBJECTS IN. Some UDTFs not appearing.",
        ),
        (
            "Compliance dashboard showing stale metrics",
            "Horizon compliance dashboard showing metrics from 5 days ago. Last_refreshed timestamp not updating. Governance checks passing but dashboard frozen.",
        ),
    ],
    "Unistore & Hybrid Tables": [
        (
            "Hybrid table INSERT latency exceeds 100ms",
            "Hybrid table INSERT statements taking 200-500ms. Documentation promises sub-100ms. Table has 1M rows, PRIMARY KEY on ID. No secondary indexes.",
        ),
        (
            "Unistore workload not using query acceleration",
            "Unistore queries not engaging Query Acceleration Service despite high row scan. Queries touching 10M+ rows but QAS not shown in query profile.",
        ),
        (
            "Hybrid table key rotation taking 6 hours",
            "Tri-Secret Secure key rotation on hybrid table taking 6 hours for 50GB table. Blocking all writes. Documentation estimates 'minutes' for this size.",
        ),
    ],
    "Container Services & Kubernetes": [
        (
            "Container Services compute pool stuck STARTING",
            "Compute pool for Snowpark Container Services stuck in STARTING state for 45 minutes. Expected startup < 5 minutes. Pool size is SMALL (2 nodes).",
        ),
        (
            "Service function deployment failing validation",
            "Service function deployment failing with 'image validation error'. Image pulled successfully from Docker Hub. Requirements.txt and handler defined.",
        ),
        (
            "Job service OOM despite 4GB memory limit",
            "Job service crashing with OOM. Container spec defines 4GB memory. Application heap size 2GB. Docker stats shows 3.2GB usage before crash.",
        ),
    ],
    "Git Integration & Version Control": [
        (
            "Git repository fetch timing out after 30s",
            "ALTER GIT REPOSITORY FETCH timing out. Private GitHub repo, 200MB size. Works via git clone locally. API integration has correct token. Fetch timeout 30s.",
        ),
        (
            "Git branch switch not reflecting in stage",
            "ALTER GIT REPOSITORY SET BRANCH='develop' succeeds but files in @repo still from 'main'. SHOW GIT BRANCHES shows develop as HEAD. Stage browser shows old files.",
        ),
        (
            "Notebook Git push failing with merge conflict",
            "Snowflake Notebook auto-push to Git failing. Error: 'push rejected - merge required'. Local branch ahead by 2 commits. No conflict resolution UI.",
        ),
    ],
    "Snowflake Openflow": [
        (
            "Openflow connector sync failing intermittently",
            "Salesforce connector in Openflow syncing 90% of records then failing. Error: 'API rate limit exceeded'. Salesforce API limits not reached on their side.",
        ),
        (
            "Openflow schedule not running at configured time",
            "Openflow schedule configured for 02:00 UTC but running at random times between 02:00-04:00. Requires consistent timing for downstream processing.",
        ),
    ],
    "Cross-Region & Cross-Cloud": [
        (
            "Cross-cloud share latency high (AWS to Azure)",
            "Data share from AWS us-east-1 account to Azure westus2 consumer showing 500ms query latency. Same-cloud shares are 50ms. Network path issue suspected.",
        ),
        (
            "Iceberg table cross-region egress unexpected",
            "Iceberg table in S3 us-west-2 but account in us-east-1. Egress charges $2K/month. Expected Snowflake to read from S3 without cross-region transfer.",
        ),
    ],
    "Directory Tables & Unstructured Data": [
        (
            "Directory table not detecting new S3 files",
            "Directory table not showing files added to external stage in last 24 hours. ALTER STAGE REFRESH runs successfully. Files visible in S3 console.",
        ),
        (
            "GET_PRESIGNED_URL failing with 403 error",
            "SELECT GET_PRESIGNED_URL(@stage, 'file.pdf') returning URL that gives 403 Forbidden. Stage has external S3 location. IAM policy allows s3:GetObject.",
        ),
    ],
    "Query Profile & Observability": [
        (
            "Query profile missing operator statistics",
            "Query profile showing operators but Statistics pane empty. Query ran for 45 minutes. Profile states 'statistics collection disabled'. No parameter to enable found.",
        ),
        (
            "Query Insights not showing recommendations",
            "Query Insights pane empty for expensive queries. Documentation shows examples of partition pruning suggestions. Queries scanning 1TB+ per execution.",
        ),
        (
            "QUERY_HISTORY view missing recent queries",
            "QUERY_HISTORY in ACCOUNT_USAGE missing queries from last 2 hours. Information_schema.query_history shows them. UI Snowsight query history also has gap.",
        ),
    ],
    "Event Tables & Logging": [
        (
            "Event table entries not appearing",
            "Event table configured for account but SYSTEM$LOG calls not creating entries. Event table exists and is accessible. Tested with INFO/ERROR levels.",
        ),
        (
            "Native App logs not showing in consumer account",
            "Native App logging enabled but consumer cannot see logs in event table. Event sharing configured. Provider can see logs in their account.",
        ),
    ],
    "Streamlit": [
        (
            "Streamlit app warehouse not suspending",
            "Streamlit app warehouse running for 6 hours after last use. WebSocket connection shows expired 5.5 hours ago. Auto-suspend set to 5 minutes. Warehouse manually suspendable.",
        ),
        (
            "Streamlit session state lost on refresh",
            "st.session_state losing values on browser refresh. Using st.cache_resource for session persistence. State includes 200MB dataframe. Local testing works.",
        ),
        (
            "Streamlit app deployment failing validation",
            "CREATE STREAMLIT failing with 'environment validation error'. Requirements.txt specifies pandas==2.0.0. Works in local Streamlit 1.40. FROM @stage syntax used.",
        ),
    ],
    "Dynamic Tables": [
        (
            "Dynamic table refresh failing - target lag exceeded",
            "Dynamic table falling behind target lag (5 minutes). Actual lag is 45 minutes. Base table updates every minute. Dynamic table query takes 30 seconds to run.",
        ),
        (
            "Immutability constraint blocking incremental refresh",
            "Dynamic table with immutability constraints not doing incremental refresh. Full refresh happening every time. Constraint is simple WHERE created_at < '2025-01-01'.",
        ),
        (
            "Dynamic table not detecting base table changes",
            "Dynamic table not refreshing despite base table inserts. Target lag is 1 minute. SHOW DYNAMIC TABLES shows REFRESH_MODE=AUTO. Manual refresh works.",
        ),
    ],
    "Native App Framework": [
        (
            "Native App installation failing privilege error",
            "Consumer installing Native App getting 'insufficient privileges on APPLICATION ROLE'. App manifest defines required privileges. ACCOUNTADMIN installing.",
        ),
        (
            "Application package version not showing in listing",
            "Published new version (v1.2.0) but listing still showing v1.1.0. Version is set as DEFAULT. Wait time 48 hours but still old version showing.",
        ),
        (
            "Container services in Native App not starting",
            "Native App with Snowpark Container Services failing to start compute pool. Consumer account has container services enabled. Pool spec defines 2 SMALL nodes.",
        ),
        (
            "Native App query history redaction exposing logic",
            "Native App query text appearing in consumer's QUERY_HISTORY view. IP protection should redact queries. Checked manifest - redaction enabled.",
        ),
    ],
}

COMPANIES = [
    "DataFlow Dynamics",
    "CloudVault Systems",
    "Quantum Analytics Corp",
    "Apex Data Solutions",
    "Silverline Technologies",
    "Horizon Intelligence",
    "TechNova Industries",
    "Global Insights Ltd",
    "Pinnacle Data Group",
    "NextGen Analytics",
    "Fusion Data Labs",
    "Stratus Computing",
    "Meridian Systems",
    "Vertex Data Corp",
    "Eclipse Technologies",
    "Summit Analytics",
    "Cascade Data Solutions",
    "Ember Intelligence",
    "Prism Data Group",
    "Nexus Tech Solutions",
]

STATUS_DISTRIBUTION = [
    ("Closed", 0.70),
    ("In Progress", 0.15),
    ("New", 0.10),
    ("Solution Provided", 0.03),
    ("Awaiting Customer", 0.02),
]

SEVERITY_DISTRIBUTION = [
    ("Severity-4: Low impact to business/operations", 0.50),
    ("Severity-3: Medium to low impact to business/operations", 0.30),
    ("Severity-2: High impact, but business is operational", 0.15),
    ("Severity-1: Critical outage", 0.05),
]


def weighted_choice(choices: list[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in choices)
    r = random.uniform(0, total)
    upto = 0
    for choice, weight in choices:
        if upto + weight >= r:
            return choice
        upto += weight
    return choices[0][0]


def generate_timestamps(status: str, days_ago_range: tuple[int, int] = (1, 90)):
    days_ago = random.randint(*days_ago_range)
    created_at = datetime.now() - timedelta(days=days_ago)

    if status == "Closed" or status == "Solution Provided":
        resolution_hours = random.uniform(1, 168)
        closed_at = created_at + timedelta(hours=resolution_hours)
        updated_at = closed_at
        last_modified_at = closed_at
        return created_at, updated_at, closed_at, last_modified_at, resolution_hours
    else:
        hours_open = random.uniform(1, days_ago * 24)
        updated_at = created_at + timedelta(hours=hours_open)
        last_modified_at = updated_at
        return created_at, updated_at, None, last_modified_at, None


def generate_fake_cases(n: int, start_case_number: int = 1000) -> str:
    """
    Generate n fake Snowflake support cases with realistic data.

    Args:
        n: Number of cases to generate
        start_case_number: Starting case number (default 1000)

    Returns:
        SQL INSERT statement ready for execution
    """
    cases = []

    for i in range(n):
        case_id = f"500FAKE{str(start_case_number + i).zfill(7)}"
        case_number = f"{str(start_case_number + i).zfill(8)}"

        topic = random.choice(TOPICS)
        if topic in CASE_TEMPLATES:
            subject, description = random.choice(CASE_TEMPLATES[topic])
        else:
            subject = f"{topic} issue"
            description = f"Customer reported issue related to {topic}"

        category = random.choice(list(PRODUCTS_BY_CATEGORY.keys()))
        product = random.choice(PRODUCTS_BY_CATEGORY[category])

        status = weighted_choice(STATUS_DISTRIBUTION)
        severity = weighted_choice(SEVERITY_DISTRIBUTION)

        created_at, updated_at, closed_at, last_modified_at, resolution_hours = generate_timestamps(status)

        account_name = random.choice(COMPANIES)
        account_id = f"001ACCT{random.randint(1000, 9999)}"

        created_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
        updated_str = updated_at.strftime("%Y-%m-%d %H:%M:%S")
        closed_str = closed_at.strftime("%Y-%m-%d %H:%M:%S") if closed_at else "NULL"
        modified_str = last_modified_at.strftime("%Y-%m-%d %H:%M:%S")
        resolution_str = f"{resolution_hours:.1f}" if resolution_hours else "NULL"

        subject_escaped = subject.replace("'", "''")
        description_escaped = description.replace("'", "''")
        closed_value = closed_str if closed_str == "NULL" else f"'{closed_str}'"
        case_values = (
            f"('{case_id}', '{case_number}', '{created_str}', '{updated_str}', "
            f"{closed_value}, "
            f"'{modified_str}', '{status}', '{severity}', '{subject_escaped}', "
            f"'{description_escaped}', '{account_id}', '{account_name}', "
            f"'{topic}', '{category}', '{product}', {resolution_str})"
        )

        cases.append(case_values)
    sql = f"""INSERT INTO CASES (
    ID, CASE_NUMBER, CREATED_AT, UPDATED_AT, CLOSED_AT, LAST_MODIFIED_AT,
    STATUS, SEVERITY, SUBJECT, DESCRIPTION, ACCOUNT_ID, ACCOUNT_NAME,
    GENERATED_TOPIC, GENERATED_PRODUCT_CATEGORY, GENERATED_PRODUCT, RESOLUTION_TIME_HOURS
) VALUES
{",".join(cases)}"""

    return sql
if __name__ == "__main__":
    print("Generating 5 fake cases...")
    print(generate_fake_cases(5))
