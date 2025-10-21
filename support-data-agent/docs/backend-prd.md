# **Technical PRD: Support Intelligence Backend Service**
## **FastAPI + Snowflake + Snowpark**

**Version:** 1.0
**Date:** October 2025
**Author:** Technical PM
**Status:** Draft for Backend Engineering Team

---

## **Executive Summary**

Build an elegant, performant FastAPI backend service that:
- Connects Snowflake support data to analytics dashboard
- Enables AI-powered field enrichment using Snowflake Cortex
- Pre-aggregates metrics for sub-second dashboard response times
- Supports flexible data source configuration

**Design Principles:**
1. **Simple**: Minimize dependencies, use Snowflake-native features
2. **Elegant**: Clean code, dependency injection, async/await throughout
3. **Performant**: Smart caching, efficient batch processing, pre-aggregation

---

## **1. Architecture Overview**

### **1.1 System Design**

```
┌─────────────────┐
│   Next.js UI    │
└────────┬────────┘
         │ REST API (JSON)
         ↓
┌─────────────────────────────────────┐
│       FastAPI Application           │
│  ┌─────────────────────────────┐   │
│  │   Routers (Endpoints)       │   │
│  │  • /dashboard  • /admin     │   │
│  │  • /tickets    • /chat      │   │
│  └─────────┬───────────────────┘   │
│            ↓                        │
│  ┌─────────────────────────────┐   │
│  │   Services (Business Logic) │   │
│  │  • ConfigService             │   │
│  │  • AnalyticsService          │   │
│  │  • EnrichmentService         │   │
│  └─────────┬───────────────────┘   │
│            ↓                        │
│  ┌─────────────────────────────┐   │
│  │   Data Access Layer         │   │
│  │  • SnowflakeClient (Snowpark)│  │
│  └─────────┬───────────────────┘   │
└────────────┼───────────────────────┘
             ↓
   ┌─────────────────────┐
   │   Snowflake         │
   │  • Raw Tables       │
   │  • Enriched Tables  │
   │  • Aggregates       │
   │  • Cortex LLM       │
   │  • Tasks (Jobs)     │
   └─────────────────────┘
```

### **1.2 Technology Stack**

| Layer | Technology | Why |
|-------|-----------|-----|
| **API** | FastAPI 0.104+ | Fast, async, auto-docs |
| **Data Processing** | Snowpark Python | Native Snowflake, efficient |
| **Database** | Snowflake | Data warehouse + compute |
| **AI/ML** | Snowflake Cortex | Native LLM, no external API |
| **Job Orchestration** | Snowflake Tasks | Serverless, native |
| **Validation** | Pydantic V2 | Type safety, fast |
| **Auth** | JWT | Stateless, simple |
| **Deployment** | Docker + K8s | Standard, scalable |

**What We're NOT Using (Initially):**
- ❌ Celery (use Snowflake Tasks instead)
- ❌ Redis (use Snowflake result cache)
- ❌ External LLM APIs (use Cortex)
- ❌ ORMs (use Snowpark DataFrames)

---

## **2. Project Structure**

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings (Pydantic BaseSettings)
│   ├── dependencies.py         # DI: get_db, get_current_user
│   │
│   ├── routers/
│   │   ├── dashboard.py        # /api/v1/dashboard/*
│   │   ├── admin.py            # /api/v1/admin/*
│   │   ├── tickets.py          # /api/v1/tickets
│   │   └── chat.py             # /api/v1/chat/*
│   │
│   ├── services/
│   │   ├── analytics.py        # Analytics aggregation logic
│   │   ├── config.py           # Configuration management
│   │   ├── enrichment.py       # Field generation with Cortex
│   │   └── query.py            # Dashboard queries
│   │
│   ├── models/
│   │   ├── requests.py         # Request schemas (Pydantic)
│   │   └── responses.py        # Response schemas (Pydantic)
│   │
│   ├── db/
│   │   ├── snowflake.py        # Snowpark session management
│   │   ├── queries.py          # SQL/Snowpark query builders
│   │   └── schemas.py          # Table schemas as Python classes
│   │
│   └── utils/
│       ├── auth.py             # JWT creation/validation
│       ├── cache.py            # Simple in-memory cache
│       └── errors.py           # Custom exceptions
│
├── tests/
│   ├── test_routers/
│   ├── test_services/
│   └── test_db/
│
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## **3. API Specification**

### **3.1 Base URL & Versioning**
```
Base URL: https://api.support-intelligence.company.com
Version: /api/v1
```

### **3.2 Authentication**
All endpoints require Bearer token authentication:
```http
Authorization: Bearer <JWT_TOKEN>
```

---

## **3.3 Dashboard APIs** (Performance Critical)

### **GET /api/v1/dashboard/kpis**

Get pre-aggregated KPI metrics (Total Cases, Avg Case Life, Resolution Rate).

**Query Parameters:**
```typescript
{
  period: 'week' | 'month' | 'custom'
  startDate?: string  // ISO 8601 date (required if period='custom')
  endDate?: string    // ISO 8601 date (required if period='custom')
  products?: string[] // Filter by product names
  topics?: string[]   // Filter by topic names
  categories?: string[] // Filter by product categories
}
```

**Response:**
```json
{
  "avgCases": {
    "id": "total_cases",
    "name": "Total Cases",
    "value": 1420,
    "previousValue": 1216,
    "change": 204,
    "changePercentage": 16.8,
    "changeType": "increase",
    "period": "week",
    "comparisonPeriod": "Previous week",
    "unit": "cases",
    "drillDownEnabled": true
  },
  "avgCaseLife": {
    "id": "avg_case_life",
    "name": "Average Case Life",
    "value": 18.2,
    "previousValue": 35.7,
    "change": -17.5,
    "changePercentage": -49.0,
    "changeType": "decrease",
    "period": "week",
    "comparisonPeriod": "Previous week",
    "unit": "hours",
    "drillDownEnabled": true
  },
  "resolutionRate": {
    "id": "resolution_rate",
    "name": "Resolution Rate",
    "value": 90.7,
    "previousValue": 89.0,
    "change": 1.7,
    "changePercentage": 1.9,
    "changeType": "increase",
    "period": "week",
    "comparisonPeriod": "Previous week",
    "unit": "%",
    "drillDownEnabled": true
  }
}
```

**Performance Target:** < 300ms
**Implementation Strategy:**
- Query pre-aggregated `KPI_SUMMARY` table
- Use Snowflake result cache (identical queries return instantly)
- Application-level cache (5 min TTL)

---

### **GET /api/v1/dashboard/products**

Get product-level metrics with drill-down data.

**Query Parameters:** Same as KPIs endpoint

**Response:**
```json
[
  {
    "productId": "data-warehousing-query-performance",
    "productName": "Query Performance",
    "productCategory": "Data Warehousing",
    "parentProduct": null,
    "metrics": {
      "totalCases": {
        "id": "total_cases",
        "name": "Total Cases",
        "value": 234,
        "previousValue": 189,
        "change": 45,
        "changePercentage": 23.8,
        "changeType": "increase",
        "period": "week",
        "comparisonPeriod": "Previous week",
        "unit": "cases",
        "drillDownEnabled": true
      },
      "avgCaseLife": { /* KPIMetric */ },
      "resolutionRate": { /* KPIMetric */ }
    },
    "topIssues": [
      { "issue": "Query Optimization not working properly", "count": 92 },
      { "issue": "Search Optimization Service issues", "count": 65 }
    ],
    "trend": [
      { "date": "2025-10-07", "value": 95 },
      { "date": "2025-10-08", "value": 39 }
    ],
    "issueSummary": "Customers are experiencing slow query performance, particularly with complex joins and large result sets. The primary pain points are unexpectedly long execution times after recent configuration changes.",
    "commonPatterns": "Query optimization failures, search optimization service timeouts, result set materialization delays",
    "rootCauses": "Warehouse sizing issues, missing clustering keys on large tables, inefficient query patterns with multiple nested subqueries",
    "customerImpact": "Business-critical reports are delayed, affecting decision-making timelines. Data analysts are unable to meet SLAs for executive dashboards."
  }
]
```

**Performance Target:** < 500ms
**Implementation Strategy:** Query pre-aggregated `PRODUCTS` table

---

### **GET /api/v1/dashboard/topics**

Get topic-level metrics with sentiment analysis.

**Query Parameters:** Same as KPIs endpoint

**Response:**
```json
[
  {
    "topicId": "performance-optimization",
    "topicName": "Performance & Optimization",
    "totalCases": 187,
    "change": 23,
    "changePercentage": 14.0,
    "changeType": "increase",
    "avgResolutionTime": 24.5,
    "resolutionRate": 82.3,
    "sentiment": {
      "positive": 25,
      "neutral": 45,
      "negative": 30
    },
    "topProducts": [
      { "product": "Query Performance", "count": 76 },
      { "product": "Virtual Warehouses", "count": 54 }
    ],
    "topicDescription": "This topic covers issues related to query execution speed, optimization, and overall system performance. It includes warehouse sizing, query plan optimization, and resource allocation concerns.",
    "issueSummary": "Customers report degraded query performance, slow dashboard loads, and timeout errors. Main concerns are around complex queries taking significantly longer than expected and warehouse resource exhaustion.",
    "sentimentSummary": "Customer sentiment is predominantly frustrated, with users expressing urgency due to business impact. Some positive mentions of support responsiveness, but overall negative due to performance degradation affecting production workloads.",
    "commonThemes": "Query timeouts, slow dashboard rendering, warehouse auto-scaling issues, result cache misses, clustering key optimization needs"
  }
]
```

**Performance Target:** < 400ms
**Implementation Strategy:** Query pre-aggregated `TOPICS` table

---

## **3.4 Admin APIs - Data Source Configuration**

### **GET /api/v1/admin/databases**

List available Snowflake databases the service user can access.

**Response:**
```json
[
  "ANALYTICS_DB",
  "SUPPORT_DB",
  "PRODUCTION_DB"
]
```

**Performance Target:** < 200ms
**Cache:** 5 minutes

---

### **GET /api/v1/admin/schemas**

List schemas in a specified database.

**Query Parameters:**
```typescript
{
  database: string
}
```

**Response:**
```json
[
  "PUBLIC",
  "SUPPORT_DATA",
  "TICKETS"
]
```

**Performance Target:** < 200ms
**Cache:** 5 minutes

---

### **GET /api/v1/admin/tables**

List tables in a schema with row counts.

**Query Parameters:**
```typescript
{
  database: string
  schema: string
}
```

**Response:**
```json
[
  {
    "name": "SUPPORT_TICKETS",
    "rowCount": 523456
  },
  {
    "name": "CUSTOMER_FEEDBACK",
    "rowCount": 234567
  },
  {
    "name": "PRODUCT_ISSUES",
    "rowCount": 123456
  }
]
```

**Performance Target:** < 300ms

---

### **GET /api/v1/admin/tables/analyze**

Analyze table structure - return column names and data types.

**Query Parameters:**
```typescript
{
  database: string
  schema: string
  table: string
}
```

**Response:**
```json
[
  "CASE_ID",
  "CASE_NUMBER",
  "CREATED_AT",
  "UPDATED_AT",
  "CLOSED_AT",
  "STATUS",
  "SEVERITY",
  "SUBJECT",
  "DESCRIPTION",
  "ACCOUNT_ID",
  "ACCOUNT_NAME",
  "PRIME_CASE_STRUCTURED",
  "CHRONICLE_XML",
  "LAST_MODIFIED_AT"
]
```

**Performance Target:** < 400ms

---

### **GET /api/v1/admin/tables/preview**

Get sample rows from a table for preview.

**Query Parameters:**
```typescript
{
  database: string
  schema: string
  table: string
  limit?: number  // Default: 10, Max: 100
}
```

**Response:**
```json
{
  "columns": [
    "CASE_ID",
    "CASE_NUMBER",
    "CREATED_AT",
    "STATUS",
    "SEVERITY",
    "SUBJECT",
    "DESCRIPTION",
    "ACCOUNT_NAME"
  ],
  "rows": [
    {
      "CASE_ID": "500ABC123XYZ",
      "CASE_NUMBER": "01000096",
      "CREATED_AT": "2025-09-15",
      "STATUS": "Closed",
      "SEVERITY": "Severity-4: Low impact to business/operations",
      "SUBJECT": "Query performance degradation",
      "DESCRIPTION": "Query latency increased from 2s to 50s...",
      "ACCOUNT_NAME": "Capital One"
    }
  ],
  "sampleCount": 10
}
```

**Performance Target:** < 500ms

---

## **3.5 Admin APIs - Configuration Management**

### **POST /api/v1/admin/configurations**

Create a new data source configuration.

**Request Body:**
```json
{
  "name": "Support Tickets Configuration",
  "database": "SUPPORT_DB",
  "schema": "TICKETS",
  "tables": ["SUPPORT_TICKETS"],
  "outputTable": "SUPPORT_TICKETS_ENRICHED",
  "mappings": [
    {
      "targetField": "case_id",
      "sourceType": "column",
      "sourceColumn": "CASE_ID"
    },
    {
      "targetField": "case_number",
      "sourceType": "column",
      "sourceColumn": "CASE_NUMBER"
    },
    {
      "targetField": "topic",
      "sourceType": "generated",
      "sourceColumns": ["SUBJECT", "DESCRIPTION"],
      "aiInstruction": "Classify the support ticket into one of these topics: Performance & Optimization, Authentication & Access, Data Loading & Ingestion, Data Sharing & Collaboration, Billing & Credit Consumption, Configuration & Setup, Connectivity & Integration, Replication & DR, Compliance & Security, Storage & Data Retention, Query Errors, Feature Requests",
      "generationType": "llm",
      "generationConfig": {
        "model": "mistral-large",
        "temperature": 0.3
      }
    },
    {
      "targetField": "product",
      "sourceType": "generated",
      "sourceColumns": ["SUBJECT", "DESCRIPTION"],
      "aiInstruction": "Identify the Snowflake product this ticket is about: Query Performance, Data Storage, Virtual Warehouses, Snowpipe, Tasks & Streams, Stored Procedures, Secure Data Sharing, Data Marketplace, Replication, Authentication, Access Control, Auditing & Compliance, Snowpark, External Functions, Connectors, External Tables, Storage Integration, File Formats",
      "generationType": "llm"
    }
  ]
}
```

**Field Mapping Types:**
1. **Direct Column Mapping** (`sourceType: "column"`):
   - Maps source column 1:1 to target field
   - Example: `CASE_ID` → `case_id`

2. **JSON Path Extraction** (`sourceType: "json_path"`):
   - Extracts value from JSON column using JSON path
   - Example: Extract from `PRIME_CASE_STRUCTURED` column

3. **AI Generation** (`sourceType: "generated"`):
   - Uses LLM to generate field value from context
   - Requires `sourceColumns` (context), `aiInstruction`, `generationType`

**Response:**
```json
{
  "configId": "config_1697123456789",
  "status": "draft",
  "createdAt": "2025-10-13T18:00:00Z"
}
```

**Validation Rules:**
- Configuration name must be unique
- Output table name must not conflict with existing tables
- Required mappings: `case_id`, `case_number`, `created_at`
- AI generation must specify at least one source column

**Performance Target:** < 800ms

---

### **GET /api/v1/admin/configurations**

List all configurations.

**Response:**
```json
[
  {
    "configId": "config_1697123456789",
    "name": "Support Tickets Configuration",
    "database": "SUPPORT_DB",
    "schema": "TICKETS",
    "tables": ["SUPPORT_TICKETS"],
    "createdAt": "2025-10-13T18:00:00Z",
    "status": {
      "baseTable": { "created": true, "rowCount": 523456 },
      "topicMetrics": { "created": true, "rowCount": 12 },
      "productMetrics": { "created": true, "rowCount": 18 },
      "kpiSummary": { "created": true }
    }
  }
]
```

**Performance Target:** < 200ms

---

### **GET /api/v1/admin/configurations/{configId}**

Get detailed configuration information.

**Response:**
```json
{
  "config": {
    "name": "Support Tickets Configuration",
    "database": "SUPPORT_DB",
    "schema": "TICKETS",
    "tables": ["SUPPORT_TICKETS"],
    "mappings": [
      {
        "targetField": "case_id",
        "sourceType": "column",
        "sourceColumn": "CASE_ID"
      }
    ],
    "outputTable": "SUPPORT_TICKETS_ENRICHED",
    "createdAt": "2025-10-13T18:00:00Z"
  },
  "status": {
    "baseTable": { "created": true, "rowCount": 523456 },
    "topicMetrics": { "created": true, "rowCount": 12 },
    "productMetrics": { "created": true, "rowCount": 18 },
    "kpiSummary": { "created": true }
  }
}
```

**Performance Target:** < 300ms

---

### **DELETE /api/v1/admin/configurations/{configId}**

Delete a configuration and associated tables.

**Response:**
```json
{
  "success": true,
  "message": "Configuration and associated tables deleted successfully"
}
```

**Behavior:**
- Drops output table and aggregation tables
- Deletes configuration record
- Cancels any running jobs for this configuration

**Performance Target:** < 200ms

---

## **3.6 Admin APIs - Field Generation**

### **POST /api/v1/admin/generate**

Start field generation job (asynchronous).

**Request Body:**
```json
{
  "configId": "config_1697123456789",
  "database": "SUPPORT_DB",
  "schema": "TICKETS",
  "tables": ["SUPPORT_TICKETS"],
  "mappings": [ /* FieldMapping[] */ ]
}
```

**Response:**
```json
{
  "jobId": "job_1697123456789"
}
```

**Behavior:**
1. Creates Snowflake stored procedure for batch processing
2. Submits as Snowflake Task (serverless execution)
3. Returns job ID immediately
4. Client polls `/jobs/{jobId}` for status

**Performance Target:** < 200ms (job queued, not completed)

---

### **GET /api/v1/admin/jobs/{jobId}**

Get job status and progress.

**Response:**
```json
{
  "jobId": "job_1697123456789",
  "status": "processing",
  "progress": 45,
  "estimatedTime": 120,
  "results": {
    "processed": 235602,
    "errors": 3
  }
}
```

**Status Values:**
- `queued`: Job created, not started yet
- `processing`: Job is running
- `completed`: Job finished successfully
- `failed`: Job encountered fatal error

**Performance Target:** < 100ms

---

### **POST /api/v1/admin/analytics/{configId}**

Run analytics aggregation (creates pre-aggregated tables).

**Response:**
```json
{
  "analyticsJobId": "analytics_1697123456789"
}
```

**Behavior:**
1. Aggregates topic metrics (33% progress)
2. Aggregates product metrics (66% progress)
3. Calculates KPI summary (100% progress)

**Performance Target:** < 300ms (job queued)
**Actual Processing Time:** ~5 minutes for 500K tickets

---

## **3.7 Tickets API**

### **GET /api/v1/tickets**

Get paginated list of tickets with filters.

**Query Parameters:**
```typescript
{
  page: number           // Default: 1
  pageSize: number       // Default: 50, Max: 100
  sortBy?: string        // Default: 'created_at'
  sortOrder?: 'asc' | 'desc'  // Default: 'desc'

  // Filters
  period?: 'week' | 'month' | 'custom'
  startDate?: string
  endDate?: string
  products?: string[]
  topics?: string[]
  categories?: string[]
  statuses?: string[]    // Filter by ticket status
  severities?: string[]  // Filter by severity
}
```

**Response:**
```json
{
  "tickets": [
    {
      "id": "500ABC123XYZ",
      "case_number": "01000096",
      "created_at": "2025-09-15T10:30:00Z",
      "updated_at": "2025-09-17T14:20:00Z",
      "closed_at": "2025-09-17T14:20:00Z",
      "status": "Closed",
      "severity": "Severity-4: Low impact to business/operations",
      "subject": "Query performance degradation",
      "description": "Query latency increased from 2s to 50s after enabling feature X",
      "account_name": "Capital One",
      "generated_topic": "Performance & Optimization",
      "generated_product": "Query Performance",
      "resolution_time_hours": 52.8,
      "sla_violated": false
    }
  ],
  "total": 523456,
  "page": 1,
  "pageSize": 50
}
```

**Performance Target:** < 400ms

---

## **3.8 Chat API**

### **POST /api/v1/chat/messages**

Natural language query interface (uses Cortex for SQL generation).

**Request Body:**
```json
{
  "message": "What are the top issues this week?",
  "sessionId": "session_abc123"
}
```

**Response:**
```json
{
  "response": "The top issues this week are:\n1. Query Performance (234 cases) - up 23% from last week\n2. Connection Timeout (189 cases) - up 15%\n3. Permission Denied (156 cases) - down 5%\n\nQuery performance issues are primarily affecting the Data Warehousing product category.",
  "suggestedQueries": [
    "What products have the most issues?",
    "Show me the resolution rate trend",
    "Which accounts are most affected by query performance issues?"
  ]
}
```

**Flow:**
1. User sends natural language query
2. Build prompt with schema context
3. Call Snowflake Cortex COMPLETE() to generate SQL
4. Validate generated SQL (ensure SELECT only, no DDL/DML)
5. Execute SQL with 30-second timeout
6. Format results as natural language response
7. Generate suggested follow-up queries

**Performance Target:** < 1500ms (includes LLM call)

**Safety:**
- Only allow SELECT queries
- Reject DDL/DML queries
- Timeout after 30 seconds
- Limit result set to 1000 rows

---

## **4. Data Models (Snowflake Schema)**

### **4.1 Configuration Table**

```sql
CREATE TABLE CONFIGURATIONS (
  CONFIG_ID VARCHAR(50) PRIMARY KEY,
  NAME VARCHAR(255) NOT NULL UNIQUE,
  DATABASE_NAME VARCHAR(255) NOT NULL,
  SCHEMA_NAME VARCHAR(255) NOT NULL,
  TABLES ARRAY NOT NULL,
  OUTPUT_TABLE VARCHAR(255) NOT NULL,
  MAPPINGS VARIANT NOT NULL,  -- JSON array of FieldMapping
  STATUS VARCHAR(20) DEFAULT 'draft',
  CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### **4.2 Enriched Base Table (CASES)**

The `CASES` table is the core fact table that contains all enriched support case data. User provides a raw table, which is then enhanced with AI-generated taxonomy fields.

```sql
CREATE TABLE CASES (
  -- Core identifiers
  ID VARCHAR(50) PRIMARY KEY,
  CASE_NUMBER VARCHAR(20),

  -- Timestamps (indexed for time-range queries)
  CREATED_AT TIMESTAMP_NTZ,
  UPDATED_AT TIMESTAMP_NTZ,
  CLOSED_AT TIMESTAMP_NTZ,
  LAST_MODIFIED_AT TIMESTAMP_NTZ,

  -- Status and severity
  STATUS VARCHAR(50),
  SEVERITY VARCHAR(100),
  INITIAL_SEVERITY VARCHAR(100),
  PEAK_SEVERITY VARCHAR(100),

  -- Content
  SUBJECT VARCHAR(500),
  DESCRIPTION TEXT,

  -- Customer/Account
  ACCOUNT_ID VARCHAR(50),
  ACCOUNT_NAME VARCHAR(255),
  IS_PRIORITY_SUPPORT BOOLEAN,

  -- Metadata
  TOTAL_COMMENTS INTEGER,
  HAS_JIRA_ISSUES BOOLEAN,
  HAS_ESCALATIONS BOOLEAN,
  HAS_COLLABORATIONS BOOLEAN,

  -- AI-Generated Fields (indexed for analytics)
  -- Generated using SNOWFLAKE.CORTEX.AI_CLASSIFY() or AI_EXTRACT() or AI_SENTIMENT()
  GENERATED_TOPIC VARCHAR(100),
  GENERATED_PRODUCT_CATEGORY VARCHAR(100),
  GENERATED_PRODUCT VARCHAR(100),
  GENERATED_FEATURE VARCHAR(100),
  GENERATED_SENTIMENT VARCHAR(20),

  -- Resolution metrics
  RESOLUTION_TIME_HOURS FLOAT,
  SLA_VIOLATED BOOLEAN,

  -- Audit
  ENRICHED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

```

### **4.3 Pre-Aggregated Tables**

#### **TOPICS - Topic Metrics with AI Semantic Aggregation**

The `TOPICS` table contains pre-aggregated metrics for each topic, including AI-generated semantic summaries using `SNOWFLAKE.CORTEX.AI_AGG()`.

```sql
CREATE TABLE TOPICS (
  METRIC_ID VARCHAR(50) PRIMARY KEY,
  TOPIC_ID VARCHAR(100),
  TOPIC_NAME VARCHAR(200),
  PERIOD VARCHAR(20),
  START_DATE DATE,
  END_DATE DATE,

  -- Calculated Metrics (standard aggregations)
  TOTAL_CASES INTEGER,
  PREVIOUS_CASES INTEGER,
  CHANGE INTEGER,
  CHANGE_PERCENTAGE FLOAT,
  CHANGE_TYPE VARCHAR(10),
  AVG_RESOLUTION_TIME FLOAT,
  RESOLUTION_RATE FLOAT,
  SENTIMENT_POSITIVE FLOAT,
  SENTIMENT_NEUTRAL FLOAT,
  SENTIMENT_NEGATIVE FLOAT,
  TOP_PRODUCTS VARIANT,  -- JSON array: [{product: "...", count: 76}, ...]

  -- AI-Generated Semantic Fields (using AI_AGG)
  TOPIC_DESCRIPTION TEXT,      -- AI_AGG(description, 'Generate a concise description of what this topic encompasses based on case descriptions')
  ISSUE_SUMMARY TEXT,           -- AI_AGG(description, 'Summarize the main customer issues and pain points for this topic')
  SENTIMENT_SUMMARY TEXT,       -- AI_AGG(description, 'Analyze the sentiment patterns and customer emotions for this topic')
  COMMON_THEMES TEXT,           -- AI_AGG(subject, 'Extract the most common themes and patterns from case subjects')

  CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

#### **PRODUCTS - Product Metrics with AI Semantic Aggregation**

The `PRODUCTS` table contains pre-aggregated metrics for each product, including AI-generated semantic insights using `SNOWFLAKE.CORTEX.AI_AGG()`.

```sql
CREATE TABLE PRODUCTS (
  METRIC_ID VARCHAR(50) PRIMARY KEY,
  PRODUCT_ID VARCHAR(100),
  PRODUCT_NAME VARCHAR(200),
  PRODUCT_CATEGORY VARCHAR(100),
  PERIOD VARCHAR(20),
  START_DATE DATE,
  END_DATE DATE,

  -- Store KPIs as JSON for flexibility
  METRICS VARIANT,  -- {totalCases: {...}, avgCaseLife: {...}, resolutionRate: {...}}
  TOP_ISSUES VARIANT,  -- [{issue: "...", count: 92}, ...]
  TREND_DATA VARIANT,  -- [{date: "2025-10-07", value: 95}, ...]

  -- AI-Generated Semantic Fields (using AI_AGG)
  ISSUE_SUMMARY TEXT,           -- AI_AGG(description, 'Summarize the main product issues and customer pain points')
  COMMON_PATTERNS TEXT,          -- AI_AGG(subject, 'Extract common patterns and recurring themes from case subjects')
  ROOT_CAUSES TEXT,              -- AI_AGG(description, 'Identify root causes and underlying technical issues')
  CUSTOMER_IMPACT TEXT,          -- AI_AGG(description, 'Describe how these issues impact customers and their workflows')

  CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

#### **KPI_SUMMARY - Platform-Wide Metrics**

The `KPI_SUMMARY` table contains platform-wide aggregated metrics with period-over-period comparisons.

```sql
CREATE TABLE KPI_SUMMARY (
  SUMMARY_ID VARCHAR(50) PRIMARY KEY,
  PERIOD VARCHAR(20),
  START_DATE DATE,
  END_DATE DATE,

  -- Store all KPIs as structured JSON
  KPIS VARIANT,  -- {avgCases: {...}, avgCaseLife: {...}, resolutionRate: {...}}
  CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### **4.4 Job Tracking**
```sql
CREATE TABLE GENERATION_JOBS (
  JOB_ID VARCHAR(50) PRIMARY KEY,
  CONFIG_ID VARCHAR(50),
  JOB_TYPE VARCHAR(20),  -- 'field_generation' | 'analytics'
  STATUS VARCHAR(20) DEFAULT 'queued',
  PROGRESS INTEGER DEFAULT 0,
  ESTIMATED_TIME INTEGER,
  PROCESSED_RECORDS INTEGER DEFAULT 0,
  ERROR_RECORDS INTEGER DEFAULT 0,
  ERROR_MESSAGE TEXT,
  STARTED_AT TIMESTAMP_NTZ,
  COMPLETED_AT TIMESTAMP_NTZ,
  CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

---

## **5. Service Layer Implementation**

### **5.1 EnrichmentService**

Handles field generation using Snowflake Cortex LLM.

```python
class EnrichmentService:
    """Handles field generation with Snowflake Cortex"""

    def __init__(self, session: Session):
        self.session = session

    async def start_generation_job(self, request: GenerateRequest) -> str:
        """
        Create and submit Snowflake Task for field generation.
        Returns job_id immediately.
        """
        job_id = f"job_{int(time.time() * 1000)}"

        # 1. Insert job record
        self.session.sql(f"""
            INSERT INTO GENERATION_JOBS
            (JOB_ID, CONFIG_ID, JOB_TYPE, STATUS)
            VALUES ('{job_id}', '{request.config_id}', 'field_generation', 'queued')
        """).collect()

        # 2. Create stored procedure for batch processing
        proc_name = f"GENERATE_FIELDS_{job_id}"
        self._create_generation_procedure(proc_name, request)

        # 3. Submit as Snowflake Task (runs asynchronously)
        self.session.sql(f"""
            CREATE TASK TASK_{job_id}
            WAREHOUSE = COMPUTE_WH
            AS CALL {proc_name}()
        """).collect()

        self.session.sql(f"ALTER TASK TASK_{job_id} RESUME").collect()

        return job_id

    def _create_generation_procedure(self, proc_name: str, request: GenerateRequest):
        """
        Create stored procedure that:
        1. Reads source data in batches (1000 records)
        2. Applies column mappings
        3. Calls Cortex for AI generation
        4. Writes to output table
        5. Updates job progress
        """
        sql = f"""
        CREATE OR REPLACE PROCEDURE {proc_name}()
        RETURNS VARCHAR
        LANGUAGE PYTHON
        RUNTIME_VERSION = '3.10'
        PACKAGES = ('snowflake-snowpark-python')
        HANDLER = 'process_batch'
        AS
        $$
import snowflake.snowpark as sp
from snowflake.snowpark.functions import col, call_builtin, lit

def process_batch(session: sp.Session):
    # Read source table
    source_df = session.table('{request.source_table}')

    # Apply column mappings
    mapped_df = source_df.select([
        col(mapping.source_column).alias(mapping.target_field)
        for mapping in request.mappings
        if mapping.source_type == 'column'
    ])

    # Apply AI generation for generated fields using Cortex AI functions
    for mapping in [m for m in request.mappings if m.source_type == 'generated']:

        if mapping.generation_type == 'ai_classify':
            # Use AI_CLASSIFY for classification into predefined categories
            # Example: Classify topic from subject/description
            # User provides categories in aiInstruction
            categories = mapping.generation_config.get('categories', [])
            context_text = concat(
                lit("SUBJECT: "), col(mapping.source_columns[0]),
                lit(" DESCRIPTION: "), col(mapping.source_columns[1])
            )

            mapped_df = mapped_df.with_column(
                mapping.target_field,
                call_builtin("SNOWFLAKE.CORTEX.AI_CLASSIFY",
                            context_text,
                            lit(categories))
            )

        elif mapping.generation_type == 'ai_extract':
            # Use AI_EXTRACT for extracting structured information
            # Example: Extract product, severity, impact from description
            schema = mapping.generation_config.get('schema', {})

            mapped_df = mapped_df.with_column(
                mapping.target_field,
                call_builtin("SNOWFLAKE.CORTEX.AI_EXTRACT",
                            col(mapping.source_columns[0]),
                            lit(schema))
            )

        else:
            # Fallback to COMPLETE for general LLM generation
            # Build prompt with context
            prompt = lit(f"{{mapping.ai_instruction}}\\n\\nBased on: ") + \
                     lit("SUBJECT: ") + col(mapping.source_columns[0]) + \
                     lit("\\nDESCRIPTION: ") + col(mapping.source_columns[1])

            mapped_df = mapped_df.with_column(
                mapping.target_field,
                call_builtin("SNOWFLAKE.CORTEX.COMPLETE",
                            lit("mistral-large"),
                            prompt)
            )

    # Write to output table in batches
    mapped_df.write.mode("append").save_as_table('{request.output_table}')

    # Update job status
    session.sql(f"""
        UPDATE GENERATION_JOBS
        SET STATUS = 'completed',
            PROGRESS = 100,
            COMPLETED_AT = CURRENT_TIMESTAMP()
        WHERE JOB_ID = '{job_id}'
    """).collect()

    return 'SUCCESS'
$$
        """
        self.session.sql(sql).collect()

    async def get_job_status(self, job_id: str) -> JobStatus:
        """Query job status from GENERATION_JOBS table"""
        result = self.session.sql(f"""
            SELECT * FROM GENERATION_JOBS
            WHERE JOB_ID = '{job_id}'
        """).collect()

        if not result:
            raise HTTPException(404, "Job not found")

        return JobStatus.from_snowflake_row(result[0])
```

### **5.2 AnalyticsService**

Pre-aggregates metrics for fast dashboard queries.

```python
from cachetools import TTLCache

class AnalyticsService:
    """Pre-aggregates metrics for fast dashboard queries"""

    def __init__(self, session: Session):
        self.session = session
        self.cache = TTLCache(maxsize=100, ttl=300)  # 5 min cache

    async def get_kpis(self, filters: Filters) -> KPIsResponse:
        """
        Query pre-aggregated KPI_SUMMARY table.
        Target: <300ms
        """
        cache_key = f"kpis_{filters.period}_{filters.start_date}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Query pre-aggregated table
        df = self.session.table(f"{filters.output_table}_KPI_SUMMARY") \
            .filter(col("PERIOD") == filters.period) \
            .filter(col("START_DATE") == filters.start_date) \
            .select("KPIS") \
            .collect()

        if not df:
            raise HTTPException(404, "No KPI data for this period")

        # Parse JSON VARIANT column
        kpis = json.loads(df[0]["KPIS"])
        result = KPIsResponse(**kpis)

        self.cache[cache_key] = result
        return result

    async def get_product_metrics(self, filters: Filters) -> List[ProductMetrics]:
        """
        Query pre-aggregated PRODUCT_METRICS table.
        Target: <500ms
        """
        cache_key = f"products_{filters.period}_{filters.start_date}_{hash(frozenset(filters.products or []))}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        df = self.session.table(f"{filters.output_table}_PRODUCT_METRICS") \
            .filter(col("PERIOD") == filters.period) \
            .filter(col("START_DATE") == filters.start_date)

        # Apply product filter if specified
        if filters.products:
            df = df.filter(col("PRODUCT_NAME").in_(filters.products))

        results = df.collect()

        # Parse VARIANT columns and construct response
        metrics = []
        for row in results:
            metrics.append(ProductMetrics(
                productId=row["PRODUCT_ID"],
                productName=row["PRODUCT_NAME"],
                productCategory=row["PRODUCT_CATEGORY"],
                metrics=json.loads(row["METRICS"]),
                topIssues=json.loads(row["TOP_ISSUES"]),
                trend=json.loads(row["TREND_DATA"])
            ))

        self.cache[cache_key] = metrics
        return metrics

    async def run_analytics_aggregation(self, config_id: str) -> str:
        """
        Run analytics aggregation as Snowflake Task.
        Creates: TOPIC_METRICS, PRODUCT_METRICS, KPI_SUMMARY tables
        """
        job_id = f"analytics_{int(time.time() * 1000)}"

        # Create aggregation stored procedure
        self._create_aggregation_procedure(job_id, config_id)

        # Submit as task
        self.session.sql(f"""
            CREATE TASK TASK_{job_id}
            WAREHOUSE = COMPUTE_WH
            AS CALL AGGREGATE_ANALYTICS_{job_id}()
        """).collect()

        self.session.sql(f"ALTER TASK TASK_{job_id} RESUME").collect()

        return job_id
```

### **5.3 QueryService**

Handles dashboard queries with filters.

```python
class QueryService:
    """Handles dashboard queries with filters"""

    def __init__(self, session: Session):
        self.session = session

    async def get_tickets(
        self,
        page: int,
        page_size: int,
        filters: Filters
    ) -> PaginatedTickets:
        """
        Get paginated tickets with filters.
        Target: <400ms
        """
        # Build filter conditions
        conditions = [
            col("CREATED_AT") >= filters.start_date,
            col("CREATED_AT") < filters.end_date
        ]

        if filters.products:
            conditions.append(col("GENERATED_PRODUCT").in_(filters.products))

        if filters.topics:
            conditions.append(col("GENERATED_TOPIC").in_(filters.topics))

        if filters.categories:
            conditions.append(col("GENERATED_PRODUCT_CATEGORY").in_(filters.categories))

        # Query with pagination
        df = self.session.table(filters.output_table)
        for condition in conditions:
            df = df.filter(condition)

        # Count total (for pagination metadata)
        total = df.count()

        # Apply sorting
        sort_col = filters.sort_by or "CREATED_AT"
        sort_order = filters.sort_order or "desc"
        df = df.sort(col(sort_col).desc() if sort_order == "desc" else col(sort_col).asc())

        # Paginate
        offset = (page - 1) * page_size
        tickets = df.limit(page_size).offset(offset).collect()

        return PaginatedTickets(
            tickets=[Ticket.from_row(row) for row in tickets],
            total=total,
            page=page,
            pageSize=page_size
        )
```

---

## **6. Analytics Aggregation Queries**

### **6.1 Topic Metrics Aggregation with AI Semantic Summaries**

```sql
-- Aggregates metrics by topic for current and previous period
-- Includes AI_AGG for semantic field generation
INSERT INTO TOPICS
WITH current_period AS (
  SELECT
    GENERATED_TOPIC as topic_id,
    GENERATED_TOPIC as topic_name,
    COUNT(*) as total_cases,
    AVG(RESOLUTION_TIME_HOURS) as avg_resolution_time,
    SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as resolution_rate,
    SUM(CASE WHEN SENTIMENT = 'positive' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as sentiment_positive,
    SUM(CASE WHEN SENTIMENT = 'neutral' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as sentiment_neutral,
    SUM(CASE WHEN SENTIMENT = 'negative' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as sentiment_negative
  FROM CASES
  WHERE CREATED_AT >= :start_date AND CREATED_AT < :end_date
  GROUP BY GENERATED_TOPIC
),
previous_period AS (
  SELECT
    GENERATED_TOPIC as topic_id,
    COUNT(*) as total_cases
  FROM CASES
  WHERE CREATED_AT >= :prev_start_date AND CREATED_AT < :prev_end_date
  GROUP BY GENERATED_TOPIC
),
top_products_per_topic AS (
  SELECT
    GENERATED_TOPIC as topic_id,
    ARRAY_AGG(
      OBJECT_CONSTRUCT(
        'product', GENERATED_PRODUCT,
        'count', cnt
      )
    ) WITHIN GROUP (ORDER BY cnt DESC) as top_products
  FROM (
    SELECT
      GENERATED_TOPIC,
      GENERATED_PRODUCT,
      COUNT(*) as cnt,
      ROW_NUMBER() OVER (PARTITION BY GENERATED_TOPIC ORDER BY COUNT(*) DESC) as rn
    FROM CASES
    WHERE CREATED_AT >= :start_date AND CREATED_AT < :end_date
    GROUP BY GENERATED_TOPIC, GENERATED_PRODUCT
  )
  WHERE rn <= 3
  GROUP BY GENERATED_TOPIC
),
-- AI-powered semantic aggregations for topic descriptions
ai_topic_summaries AS (
  SELECT
    GENERATED_TOPIC as topic_id,
    SNOWFLAKE.CORTEX.AI_AGG(
      DESCRIPTION,
      'Generate a concise description of what this topic encompasses based on case descriptions'
    ) as topic_description,
    SNOWFLAKE.CORTEX.AI_AGG(
      DESCRIPTION,
      'Summarize the main customer issues and pain points for this topic'
    ) as issue_summary,
    SNOWFLAKE.CORTEX.AI_AGG(
      DESCRIPTION,
      'Analyze the sentiment patterns and customer emotions for this topic'
    ) as sentiment_summary,
    SNOWFLAKE.CORTEX.AI_AGG(
      SUBJECT,
      'Extract the most common themes and patterns from case subjects'
    ) as common_themes
  FROM CASES
  WHERE CREATED_AT >= :start_date AND CREATED_AT < :end_date
  GROUP BY GENERATED_TOPIC
)
SELECT
  UUID_STRING() as metric_id,
  c.topic_id,
  c.topic_name,
  :period as period,
  :start_date as start_date,
  :end_date as end_date,
  c.total_cases,
  COALESCE(p.total_cases, 0) as previous_cases,
  c.total_cases - COALESCE(p.total_cases, 0) as change,
  (c.total_cases - COALESCE(p.total_cases, 0))::FLOAT / NULLIF(p.total_cases, 0) * 100 as change_percentage,
  CASE
    WHEN c.total_cases > COALESCE(p.total_cases, 0) THEN 'increase'
    WHEN c.total_cases < COALESCE(p.total_cases, 0) THEN 'decrease'
    ELSE 'neutral'
  END as change_type,
  c.avg_resolution_time,
  c.resolution_rate,
  c.sentiment_positive,
  c.sentiment_neutral,
  c.sentiment_negative,
  t.top_products,
  -- AI-generated semantic fields
  ai.topic_description,
  ai.issue_summary,
  ai.sentiment_summary,
  ai.common_themes,
  CURRENT_TIMESTAMP() as created_at
FROM current_period c
LEFT JOIN previous_period p ON c.topic_id = p.topic_id
LEFT JOIN top_products_per_topic t ON c.topic_id = t.topic_id
LEFT JOIN ai_topic_summaries ai ON c.topic_id = ai.topic_id;
```

### **6.2 Product Metrics Aggregation with AI Semantic Insights**

```sql
-- Aggregates metrics by product and category
-- Includes AI_AGG for semantic insight generation
INSERT INTO PRODUCTS
WITH current_period AS (
  SELECT
    GENERATED_PRODUCT as product_id,
    GENERATED_PRODUCT as product_name,
    GENERATED_PRODUCT_CATEGORY as product_category,
    COUNT(*) as total_cases,
    AVG(RESOLUTION_TIME_HOURS) as avg_case_life,
    SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as resolution_rate
  FROM CASES
  WHERE CREATED_AT >= :start_date AND CREATED_AT < :end_date
  GROUP BY GENERATED_PRODUCT, GENERATED_PRODUCT_CATEGORY
),
previous_period AS (
  SELECT
    GENERATED_PRODUCT as product_id,
    COUNT(*) as total_cases,
    AVG(RESOLUTION_TIME_HOURS) as avg_case_life,
    SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as resolution_rate
  FROM CASES
  WHERE CREATED_AT >= :prev_start_date AND CREATED_AT < :prev_end_date
  GROUP BY GENERATED_PRODUCT
),
top_issues_per_product AS (
  SELECT
    GENERATED_PRODUCT as product_id,
    ARRAY_AGG(
      OBJECT_CONSTRUCT('issue', issue_text, 'count', cnt)
    ) WITHIN GROUP (ORDER BY cnt DESC) as top_issues
  FROM (
    SELECT
      GENERATED_PRODUCT,
      SUBSTRING(SUBJECT, 1, 100) as issue_text,
      COUNT(*) as cnt,
      ROW_NUMBER() OVER (PARTITION BY GENERATED_PRODUCT ORDER BY COUNT(*) DESC) as rn
    FROM CASES
    WHERE CREATED_AT >= :start_date AND CREATED_AT < :end_date
    GROUP BY GENERATED_PRODUCT, SUBSTRING(SUBJECT, 1, 100)
  )
  WHERE rn <= 3
  GROUP BY GENERATED_PRODUCT
),
trend_data_per_product AS (
  SELECT
    GENERATED_PRODUCT as product_id,
    ARRAY_AGG(
      OBJECT_CONSTRUCT(
        'date', day_date,
        'value', daily_count
      )
    ) WITHIN GROUP (ORDER BY day_date) as trend_data
  FROM (
    SELECT
      GENERATED_PRODUCT,
      DATE_TRUNC('day', CREATED_AT)::DATE as day_date,
      COUNT(*) as daily_count
    FROM CASES
    WHERE CREATED_AT >= :start_date - INTERVAL '7 days' AND CREATED_AT < :end_date
    GROUP BY GENERATED_PRODUCT, DATE_TRUNC('day', CREATED_AT)
  )
  GROUP BY GENERATED_PRODUCT
),
-- AI-powered semantic aggregations for product insights
ai_product_insights AS (
  SELECT
    GENERATED_PRODUCT as product_id,
    SNOWFLAKE.CORTEX.AI_AGG(
      DESCRIPTION,
      'Summarize the main product issues and customer pain points'
    ) as issue_summary,
    SNOWFLAKE.CORTEX.AI_AGG(
      SUBJECT,
      'Extract common patterns and recurring themes from case subjects'
    ) as common_patterns,
    SNOWFLAKE.CORTEX.AI_AGG(
      DESCRIPTION,
      'Identify root causes and underlying technical issues'
    ) as root_causes,
    SNOWFLAKE.CORTEX.AI_AGG(
      DESCRIPTION,
      'Describe how these issues impact customers and their workflows'
    ) as customer_impact
  FROM CASES
  WHERE CREATED_AT >= :start_date AND CREATED_AT < :end_date
  GROUP BY GENERATED_PRODUCT
)
SELECT
  UUID_STRING() as metric_id,
  c.product_id,
  c.product_name,
  c.product_category,
  :period as period,
  :start_date as start_date,
  :end_date as end_date,
  OBJECT_CONSTRUCT(
    'totalCases', OBJECT_CONSTRUCT(
      'id', 'total_cases',
      'name', 'Total Cases',
      'value', c.total_cases,
      'previousValue', COALESCE(p.total_cases, 0),
      'change', c.total_cases - COALESCE(p.total_cases, 0),
      'changePercentage', (c.total_cases - COALESCE(p.total_cases, 0))::FLOAT / NULLIF(p.total_cases, 0) * 100,
      'changeType', CASE
        WHEN c.total_cases > COALESCE(p.total_cases, 0) THEN 'increase'
        WHEN c.total_cases < COALESCE(p.total_cases, 0) THEN 'decrease'
        ELSE 'neutral'
      END,
      'period', :period,
      'comparisonPeriod', CONCAT('Previous ', :period),
      'unit', 'cases',
      'drillDownEnabled', TRUE
    ),
    'avgCaseLife', OBJECT_CONSTRUCT(
      'id', 'avg_case_life',
      'name', 'Average Case Life',
      'value', c.avg_case_life,
      'previousValue', COALESCE(p.avg_case_life, 0),
      'change', c.avg_case_life - COALESCE(p.avg_case_life, 0),
      'changePercentage', (c.avg_case_life - COALESCE(p.avg_case_life, 0))::FLOAT / NULLIF(p.avg_case_life, 0) * 100,
      'changeType', CASE
        WHEN c.avg_case_life < COALESCE(p.avg_case_life, 0) THEN 'decrease'
        WHEN c.avg_case_life > COALESCE(p.avg_case_life, 0) THEN 'increase'
        ELSE 'neutral'
      END,
      'period', :period,
      'comparisonPeriod', CONCAT('Previous ', :period),
      'unit', 'hours',
      'drillDownEnabled', TRUE
    ),
    'resolutionRate', OBJECT_CONSTRUCT(
      'id', 'resolution_rate',
      'name', 'Resolution Rate',
      'value', c.resolution_rate,
      'previousValue', COALESCE(p.resolution_rate, 0),
      'change', c.resolution_rate - COALESCE(p.resolution_rate, 0),
      'changePercentage', (c.resolution_rate - COALESCE(p.resolution_rate, 0))::FLOAT / NULLIF(p.resolution_rate, 0) * 100,
      'changeType', CASE
        WHEN c.resolution_rate > COALESCE(p.resolution_rate, 0) THEN 'increase'
        WHEN c.resolution_rate < COALESCE(p.resolution_rate, 0) THEN 'decrease'
        ELSE 'neutral'
      END,
      'period', :period,
      'comparisonPeriod', CONCAT('Previous ', :period),
      'unit', '%',
      'drillDownEnabled', TRUE
    )
  ) as metrics,
  i.top_issues,
  t.trend_data,
  -- AI-generated semantic fields
  ai.issue_summary,
  ai.common_patterns,
  ai.root_causes,
  ai.customer_impact,
  CURRENT_TIMESTAMP() as created_at
FROM current_period c
LEFT JOIN previous_period p ON c.product_id = p.product_id
LEFT JOIN top_issues_per_product i ON c.product_id = i.product_id
LEFT JOIN trend_data_per_product t ON c.product_id = t.product_id
LEFT JOIN ai_product_insights ai ON c.product_id = ai.product_id;
```

### **6.3 KPI Summary Aggregation**

```sql
-- Platform-wide KPIs with period-over-period comparison
INSERT INTO KPI_SUMMARY
WITH current_period AS (
  SELECT
    COUNT(*) as total_cases,
    AVG(RESOLUTION_TIME_HOURS) as avg_case_life,
    SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as resolution_rate
  FROM CASES
  WHERE CREATED_AT >= :start_date AND CREATED_AT < :end_date
),
previous_period AS (
  SELECT
    COUNT(*) as total_cases,
    AVG(RESOLUTION_TIME_HOURS) as avg_case_life,
    SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as resolution_rate
  FROM CASES
  WHERE CREATED_AT >= :prev_start_date AND CREATED_AT < :prev_end_date
)
SELECT
  UUID_STRING() as summary_id,
  :period as period,
  :start_date as start_date,
  :end_date as end_date,
  OBJECT_CONSTRUCT(
    'avgCases', OBJECT_CONSTRUCT(
      'id', 'total_cases',
      'name', 'Total Cases',
      'value', c.total_cases,
      'previousValue', p.total_cases,
      'change', c.total_cases - p.total_cases,
      'changePercentage', (c.total_cases - p.total_cases)::FLOAT / p.total_cases * 100,
      'changeType', CASE
        WHEN c.total_cases > p.total_cases THEN 'increase'
        WHEN c.total_cases < p.total_cases THEN 'decrease'
        ELSE 'neutral'
      END,
      'period', :period,
      'comparisonPeriod', CONCAT('Previous ', :period),
      'unit', 'cases',
      'drillDownEnabled', TRUE
    ),
    'avgCaseLife', OBJECT_CONSTRUCT(
      'id', 'avg_case_life',
      'name', 'Average Case Life',
      'value', c.avg_case_life,
      'previousValue', p.avg_case_life,
      'change', c.avg_case_life - p.avg_case_life,
      'changePercentage', (c.avg_case_life - p.avg_case_life)::FLOAT / p.avg_case_life * 100,
      'changeType', CASE
        WHEN c.avg_case_life < p.avg_case_life THEN 'decrease'
        WHEN c.avg_case_life > p.avg_case_life THEN 'increase'
        ELSE 'neutral'
      END,
      'period', :period,
      'comparisonPeriod', CONCAT('Previous ', :period),
      'unit', 'hours',
      'drillDownEnabled', TRUE
    ),
    'resolutionRate', OBJECT_CONSTRUCT(
      'id', 'resolution_rate',
      'name', 'Resolution Rate',
      'value', c.resolution_rate,
      'previousValue', p.resolution_rate,
      'change', c.resolution_rate - p.resolution_rate,
      'changePercentage', (c.resolution_rate - p.resolution_rate)::FLOAT / p.resolution_rate * 100,
      'changeType', CASE
        WHEN c.resolution_rate > p.resolution_rate THEN 'increase'
        WHEN c.resolution_rate < p.resolution_rate THEN 'decrease'
        ELSE 'neutral'
      END,
      'period', :period,
      'comparisonPeriod', CONCAT('Previous ', :period),
      'unit', '%',
      'drillDownEnabled', TRUE
    )
  ) as kpis,
  CURRENT_TIMESTAMP() as created_at
FROM current_period c
CROSS JOIN previous_period p;
```

---

## **7. Performance Optimization**

### **7.1 Caching Strategy**

**Application-Level Cache:**
```python
from cachetools import TTLCache

class CacheService:
    """Simple in-memory TTL cache"""

    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5 min

    def get_or_compute(self, key: str, compute_fn):
        if key in self.cache:
            return self.cache[key]

        result = compute_fn()
        self.cache[key] = result
        return result
```

**Cache Keys:**
- Dashboard KPIs: `kpis_{period}_{start_date}_{filters_hash}`
- Product metrics: `products_{period}_{start_date}_{filters_hash}`
- Topic metrics: `topics_{period}_{start_date}_{filters_hash}`
- Metadata queries: `databases`, `schemas_{db}`, `tables_{db}_{schema}`

**Cache Invalidation:**
- Automatic: TTL expiration (5 minutes)
- Manual: On configuration changes, clear related keys

### **7.2 Snowflake Optimization**

**Result Caching:**
Snowflake automatically caches identical query results for 24 hours. No code changes needed - just enable in warehouse settings.

**Clustering:**
```sql
-- Cluster large tables by time for faster time-range queries
ALTER TABLE {OUTPUT_TABLE} CLUSTER BY (CREATED_AT);
```

**Indexes:**
```sql
-- Create search optimization service (automatic indexing)
ALTER TABLE {OUTPUT_TABLE} ADD SEARCH OPTIMIZATION;
```

**Materialized Views (Future Enhancement):**
```sql
-- For ultra-high performance, use materialized views
CREATE MATERIALIZED VIEW {OUTPUT_TABLE}_MV_WEEKLY_KPIS AS
SELECT
  DATE_TRUNC('week', CREATED_AT) as week_start,
  COUNT(*) as total_cases,
  AVG(RESOLUTION_TIME_HOURS) as avg_case_life,
  SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as resolution_rate
FROM {OUTPUT_TABLE}
GROUP BY DATE_TRUNC('week', CREATED_AT);
```

### **7.3 Connection Pooling**

```python
# config.py
class Settings(BaseSettings):
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_warehouse: str = "COMPUTE_WH"
    snowflake_database: str
    snowflake_schema: str

    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600  # Recycle connections after 1 hour
```

```python
# db/snowflake.py
from snowflake.snowpark import Session
from functools import lru_cache

@lru_cache()
def get_session_pool():
    """Create connection pool (singleton)"""
    return Session.builder.configs({
        "account": settings.snowflake_account,
        "user": settings.snowflake_user,
        "password": settings.snowflake_password,
        "warehouse": settings.snowflake_warehouse,
        "database": settings.snowflake_database,
        "schema": settings.snowflake_schema,
        "connection_pool_size": settings.pool_size
    }).create()

async def get_snowpark_session() -> Session:
    """Dependency injection for routes"""
    return get_session_pool()
```

### **7.4 Query Optimization Best Practices**

1. **Use Pre-Aggregation**: Query pre-aggregated tables instead of computing on-the-fly
2. **Filter Early**: Apply WHERE clauses before JOINs
3. **Limit Results**: Always use LIMIT for preview queries
4. **Use VARIANT Efficiently**: Parse JSON columns only when needed
5. **Partition Pruning**: Leverage clustering keys for time-range queries
6. **Avoid SELECT ***: Specify only needed columns

---

## **8. Deployment**

### **8.1 Docker Configuration**

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### **8.2 Environment Variables**

```bash
# .env
SNOWFLAKE_ACCOUNT=abc12345.us-west-2
SNOWFLAKE_USER=service_user
SNOWFLAKE_PASSWORD=***
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SUPPORT_DB
SNOWFLAKE_SCHEMA=TICKETS

JWT_SECRET_KEY=***
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=1

LOG_LEVEL=INFO
ENVIRONMENT=production
```

### **8.3 Kubernetes Deployment**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: support-intelligence-api
  labels:
    app: support-intelligence-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: support-intelligence-api
  template:
    metadata:
      labels:
        app: support-intelligence-api
    spec:
      containers:
      - name: api
        image: support-intelligence:latest
        ports:
        - containerPort: 8000
        env:
        - name: SNOWFLAKE_ACCOUNT
          valueFrom:
            secretKeyRef:
              name: snowflake-creds
              key: account
        - name: SNOWFLAKE_USER
          valueFrom:
            secretKeyRef:
              name: snowflake-creds
              key: user
        - name: SNOWFLAKE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: snowflake-creds
              key: password
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: support-intelligence-api
spec:
  selector:
    app: support-intelligence-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## **9. Testing Strategy**

### **9.1 Unit Tests**

```python
# tests/test_services/test_analytics.py
import pytest
from app.services.analytics import AnalyticsService
from app.models.requests import Filters

@pytest.mark.asyncio
async def test_get_kpis_returns_correct_structure(mock_session):
    service = AnalyticsService(mock_session)
    filters = Filters(period="week", start_date="2025-10-06")

    kpis = await service.get_kpis(filters)

    assert kpis.avgCases.value > 0
    assert kpis.avgCaseLife.unit == "hours"
    assert kpis.resolutionRate.unit == "%"
    assert kpis.avgCases.drillDownEnabled is True
```

### **9.2 Integration Tests**

```python
# tests/test_routers/test_dashboard.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_kpis_endpoint():
    response = client.get(
        "/api/v1/dashboard/kpis?period=week",
        headers={"Authorization": "Bearer test_token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "avgCases" in data
    assert "avgCaseLife" in data
    assert "resolutionRate" in data
    assert data["avgCases"]["drillDownEnabled"] is True
```

### **9.3 Performance Tests**

```python
# tests/test_performance.py
import pytest
import time
from fastapi.testclient import TestClient

@pytest.mark.performance
def test_kpi_endpoint_performance(client: TestClient):
    """Ensure KPI endpoint responds within 300ms"""
    start = time.time()
    response = client.get("/api/v1/dashboard/kpis?period=week")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 0.3, f"KPI endpoint took {duration}s (target: <300ms)"

@pytest.mark.performance
def test_product_metrics_performance(client: TestClient):
    """Ensure product metrics endpoint responds within 500ms"""
    start = time.time()
    response = client.get("/api/v1/dashboard/products?period=week")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 0.5, f"Product metrics took {duration}s (target: <500ms)"
```

### **9.4 Load Tests**

```python
# Use locust for load testing
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_kpis(self):
        self.client.get("/api/v1/dashboard/kpis?period=week")

    @task(2)
    def get_products(self):
        self.client.get("/api/v1/dashboard/products?period=week")

    @task(1)
    def get_topics(self):
        self.client.get("/api/v1/dashboard/topics?period=week")
```

Run: `locust -f tests/load_test.py --host=http://localhost:8000`

---

## **10. Security**

### **10.1 Authentication**

```python
# app/utils/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.config import settings

security = HTTPBearer()

def create_access_token(user_id: str) -> str:
    """Create JWT token"""
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Validate JWT and return user_id"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token")

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(401, "Token expired")

        return user_id
    except JWTError:
        raise HTTPException(401, "Invalid token")
```

**Usage in Routes:**
```python
@router.get("/kpis")
async def get_kpis(
    filters: Filters,
    user_id: str = Depends(get_current_user)
):
    # Only authenticated users can access
    ...
```

### **10.2 Input Validation**

```python
from pydantic import BaseModel, Field, validator

class ConfigCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    database: str = Field(..., regex="^[A-Z0-9_]+$")
    schema_: str = Field(..., alias="schema", regex="^[A-Z0-9_]+$")
    tables: List[str] = Field(..., min_items=1, max_items=10)
    output_table: str
    mappings: List[FieldMapping]

    @validator('output_table')
    def validate_output_table(cls, v):
        # Prevent SQL injection
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Invalid table name - must be alphanumeric")
        return v.upper()

    @validator('tables', each_item=True)
    def validate_table_names(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError("Invalid table name")
        return v.upper()
```

### **10.3 Rate Limiting**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.get("/kpis")
@limiter.limit("100/minute")
async def get_kpis(request: Request, filters: Filters):
    """Rate limited to 100 requests per minute per IP"""
    ...
```

### **10.4 SQL Injection Prevention**

Always use parameterized queries with Snowpark:

```python
# ✅ GOOD - Parameterized query
df = session.table(table_name).filter(col("STATUS") == status_value)

# ❌ BAD - String concatenation (vulnerable to SQL injection)
df = session.sql(f"SELECT * FROM {table_name} WHERE STATUS = '{status_value}'")
```

---

## **11. Monitoring & Observability**

### **11.1 Health Checks**

```python
from fastapi import status

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(session: Session = Depends(get_snowpark_session)):
    """Readiness check - verify Snowflake connectivity"""
    try:
        session.sql("SELECT 1").collect()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(503, f"Not ready: {str(e)}")
```

### **11.2 Metrics (Prometheus)**

```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

snowflake_query_duration = Histogram(
    'snowflake_query_duration_seconds',
    'Snowflake query duration',
    ['query_type']
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics"""
    return Response(generate_latest(), media_type="text/plain")
```

### **11.3 Structured Logging**

```python
import structlog
import logging

# Configure structured logging
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO
)

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

@router.get("/kpis")
async def get_kpis(filters: Filters):
    logger.info("kpi_request_received",
                period=filters.period,
                start_date=filters.start_date,
                user_id=user_id)

    try:
        start_time = time.time()
        result = await analytics.get_kpis(filters)
        duration_ms = (time.time() - start_time) * 1000

        logger.info("kpi_request_completed",
                    duration_ms=duration_ms,
                    cache_hit=False)
        return result
    except Exception as e:
        logger.error("kpi_request_failed",
                     error=str(e),
                     error_type=type(e).__name__,
                     exc_info=True)
        raise
```

### **11.4 Error Tracking (Sentry)**

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10% of transactions
    environment=settings.environment
)
```

---

## **12. Implementation Roadmap**

### **Phase 1: Foundation (Week 1)**
- [ ] FastAPI project setup with structure
- [ ] Snowpark session management and connection pooling
- [ ] Configuration management APIs (CRUD)
- [ ] Database discovery endpoints (databases, schemas, tables)
- [ ] Basic authentication (JWT creation and validation)
- [ ] Docker containerization
- [ ] Health and readiness checks

**Deliverable:** Working API with admin endpoints for data source discovery

---

### **Phase 2: Field Generation (Week 2)**
- [ ] EnrichmentService implementation
- [ ] Snowflake stored procedure for batch processing
- [ ] Cortex LLM integration for field generation
- [ ] Job tracking and status endpoints
- [ ] Error handling and retry logic
- [ ] Unit tests for enrichment service

**Deliverable:** Working field generation pipeline with AI enrichment

---

### **Phase 3: Analytics Aggregation (Week 3)**
- [ ] AnalyticsService implementation
- [ ] Topic metrics aggregation SQL and stored procedure
- [ ] Product metrics aggregation SQL and stored procedure
- [ ] KPI summary calculation SQL
- [ ] Snowflake Task orchestration for async execution
- [ ] Job polling and status updates

**Deliverable:** Automated analytics aggregation pipeline

---

### **Phase 4: Dashboard APIs (Week 4)**
- [ ] QueryService for dashboard endpoints
- [ ] KPI endpoint with caching
- [ ] Product metrics endpoint with filtering
- [ ] Topic metrics endpoint with filtering
- [ ] Filter application logic (products, topics, categories, date ranges)
- [ ] Performance optimization and query tuning
- [ ] Integration tests for all dashboard endpoints

**Deliverable:** Fast (<500ms) dashboard APIs with caching

---

### **Phase 5: Additional Features (Week 5)**
- [ ] Tickets listing endpoint with pagination
- [ ] Advanced filtering for tickets (status, severity)
- [ ] Chat/NL query endpoint (basic Cortex integration)
- [ ] Configuration deletion endpoint
- [ ] Input validation and security hardening
- [ ] Rate limiting implementation

**Deliverable:** Complete API feature set

---

### **Phase 6: Production Ready (Week 6)**
- [ ] Comprehensive unit tests (>80% coverage)
- [ ] Integration tests for all endpoints
- [ ] Performance testing and load testing
- [ ] Security audit and hardening
- [ ] Monitoring and alerting setup (Prometheus, Grafana)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Deployment to staging environment
- [ ] Load testing in staging
- [ ] Production deployment

**Deliverable:** Production-ready API service

---

## **13. Success Criteria**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Performance** |
| Dashboard KPI Load Time (p95) | < 300ms | APM monitoring |
| Product Metrics Load Time (p95) | < 500ms | APM monitoring |
| Topic Metrics Load Time (p95) | < 400ms | APM monitoring |
| Tickets List Load Time (p95) | < 400ms | APM monitoring |
| **Reliability** |
| API Uptime | 99.9% | Uptime monitoring |
| Error Rate | < 0.1% | Error tracking |
| **Scalability** |
| Field Generation Throughput | 500 records/min | Job metrics |
| Analytics Aggregation Time | < 5 min (500K tickets) | Job metrics |
| Concurrent Users Supported | 1000+ | Load testing |
| **Quality** |
| Test Coverage | > 80% | pytest-cov |
| Code Quality | A grade | SonarQube |
| Security Vulnerabilities | 0 critical/high | Security scan |

---

## **14. Open Questions & Decisions**

### **Question 1: Authentication Provider**
**Question:** Build custom JWT or integrate with company SSO (Okta, Auth0)?
**Recommendation:** Start with JWT for MVP, add SSO integration in Phase 2
**Decision:** _Pending stakeholder input_

### **Question 2: Multi-Tenancy**
**Question:** Should backend support multiple organizations/workspaces?
**Impact:** Significant schema changes, row-level security
**Recommendation:** Single-tenant for MVP, design for multi-tenant expansion
**Decision:** _Pending product decision_

### **Question 3: Real-Time Updates**
**Question:** WebSocket support for live job progress and dashboard updates?
**Recommendation:** Polling for MVP (simpler), WebSocket in Phase 2
**Decision:** _Pending product decision_

### **Question 4: LLM Provider Fallback**
**Question:** Support OpenAI as fallback if Cortex is unavailable?
**Recommendation:** Cortex only for MVP, add OpenAI option later if needed
**Decision:** _Pending architecture review_

### **Question 5: Snowflake Warehouse Management**
**Question:** Should backend auto-scale Snowflake warehouses based on load?
**Recommendation:** Use Snowflake auto-suspend/resume initially, add custom scaling logic if needed
**Decision:** _Pending infra team input_

---

## **Appendix A: Example Requests**

### **Example 1: Create Configuration**
```bash
curl -X POST https://api.support-intelligence.company.com/api/v1/admin/configurations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Support Tickets Configuration",
    "database": "SUPPORT_DB",
    "schema": "TICKETS",
    "tables": ["SUPPORT_TICKETS"],
    "outputTable": "SUPPORT_TICKETS_ENRICHED",
    "mappings": [
      {
        "targetField": "case_id",
        "sourceType": "column",
        "sourceColumn": "CASE_ID"
      },
      {
        "targetField": "topic",
        "sourceType": "generated",
        "sourceColumns": ["SUBJECT", "DESCRIPTION"],
        "aiInstruction": "Classify into: Performance, Authentication, Data Loading, etc.",
        "generationType": "llm"
      }
    ]
  }'
```

### **Example 2: Get Dashboard KPIs**
```bash
curl -X GET "https://api.support-intelligence.company.com/api/v1/dashboard/kpis?period=week" \
  -H "Authorization: Bearer <token>"
```

### **Example 3: Get Filtered Product Metrics**
```bash
curl -X GET "https://api.support-intelligence.company.com/api/v1/dashboard/products?period=week&products=Query%20Performance&products=Snowpipe" \
  -H "Authorization: Bearer <token>"
```

---

## **Appendix B: Development Setup**

### **Local Development**

```bash
# Clone repository
git clone <repo-url>
cd backend

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ --cov=app --cov-report=html
```

### **Docker Development**

```bash
# Build image
docker build -t support-intelligence-backend .

# Run container
docker run -p 8000:8000 --env-file .env support-intelligence-backend

# View logs
docker logs -f <container-id>
```

---

**End of Document**

This PRD provides a complete specification for building an elegant, simple, and performant FastAPI backend service that leverages Snowflake's native features for maximum efficiency.
