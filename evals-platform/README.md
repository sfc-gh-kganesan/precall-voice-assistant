# Evals Platform - Evaluation as a Service

A centralized evaluation infrastructure for systematic assessment of LangGraph agents across multiple projects using TruLens for deep observability.

## Overview

The Evals Platform provides a shared SPCS service that enables consistent, traceable evaluation of AI agents. It supports:
- **Multiple projects** with flexible schemas
- **Golden dataset management** with version control
- **Automated evaluation runs** with unique requestIds and timestamps
- **Detailed validation** at both extraction and decision levels
- **TruLens integration** for LLM observability and trace analysis

## Architecture

### Component Separation

**Evals Service (Centralized)**
- Dataset management and golden record storage
- Eval run orchestration across projects
- Custom validation logic per project
- TruLens integration and metrics aggregation
- REST API and dashboard

**Project-Side (Minimal Integration)**
- New eval endpoint: `POST /eval/invoke`
- Optional TruLens instrumentation (TruGraph wrapper)
- Returns structured outputs for validation

### Data Flow

```
1. Evals Service loads golden dataset from Snowflake
2. For each record, POST to project's /eval/invoke with requestId
3. Project processes request (optionally with TruGraph instrumentation)
4. TruLens captures traces to Snowflake TRULENS schema
5. Evals service validates outputs against expected results
6. Store results with requestId + timestamp
7. Dashboard aggregates and displays metrics across runs
```

## Current Status: Database Schema (✅ Complete)

### What's Been Created

The foundation database schema has been implemented:

**Database: `EVALS_PLATFORM`**

Three schemas:
- **CORE** - Evaluation management tables
- **TRULENS** - TruLens observability data (populated automatically)
- **STAGES** - File storage for golden datasets

**Tables in CORE Schema:**

1. **GOLDEN_DATASETS** - Catalog of evaluation datasets
   - `dataset_id` (PK) - Unique identifier
   - `project_name` - Which project (invoiceiq, sales-ai-platform, etc.)
   - `dataset_name` - Human-readable name
   - `stage_location` - Path to files in Snowflake stage
   - `metadata` (VARIANT) - Flexible metadata storage

2. **GOLDEN_RECORDS** - Individual test cases
   - `record_id` (PK) - Unique identifier
   - `dataset_id` - Parent dataset
   - `file_path` - Path to file in stage
   - `input_data` (VARIANT) - Inputs to agent (flexible schema per project)
   - `expected_outputs` (VARIANT) - Expected results (flexible schema per project)

3. **EVAL_RUNS** - Evaluation run tracking
   - `request_id` (PK) - Unique run identifier
   - `dataset_id` - Which dataset was evaluated
   - `project_name` - Which project
   - `run_timestamp` - When run started
   - `status` - running/completed/failed/cancelled
   - `summary_metrics` (VARIANT) - Aggregated results

4. **EVAL_RESULTS** - Detailed per-record results
   - `result_id` (PK) - Unique identifier
   - `request_id` - Parent run
   - `record_id` - Which golden record
   - `actual_outputs` (VARIANT) - What agent returned
   - `validation_results` (VARIANT) - Field-by-field comparison
   - `trulens_record_id` - Link to TruLens trace

**Views:**
- `VW_RECENT_EVAL_RUNS` - Summary of recent runs
- `VW_EVAL_RESULTS_DETAILED` - Detailed results with golden record context

**Stage:**
- `GOLDEN_DATA` - Storage for PDF files and other evaluation inputs
  - Organized by project: `@EVALS_PLATFORM.STAGES.GOLDEN_DATA/invoiceiq/`

### Design Decisions

**1. VARIANT Columns for Flexibility**
- Different projects have different schemas
- InvoiceIQ needs: extraction fields + decision
- Sales-AI might need: transcript + SFDC outputs
- VARIANT columns adapt to any structure

**2. No Enforced Constraints**
- Snowflake regular tables don't support foreign keys, indexes, or CHECK constraints
- Relationships documented in comments and enforced in application layer
- This is the Snowflake way: simple database, smart application

**3. Request ID + Timestamp Model**
- Every eval run gets unique `request_id` (UUID)
- All results tagged with same `request_id` for grouping
- Timestamps enable trend analysis over time
- Can compare runs, track improvements, detect regressions

**4. Separation of Concerns**
- Golden data (inputs + expected) stored centrally
- Actual execution delegated to project services
- Validation logic in evals service (can be project-specific)
- TruLens handles deep observability automatically

## How It Works: End-to-End Flow

### 1. Setup Phase

**Upload golden dataset files:**
```bash
# Upload 100 invoice PDFs
PUT file:///path/to/invoices/* @EVALS_PLATFORM.STAGES.GOLDEN_DATA/invoiceiq/;
```

**Create dataset entry:**
```sql
INSERT INTO GOLDEN_DATASETS VALUES (
    'invoiceiq_validation_v1',
    'invoiceiq',
    'Invoice Validation Dataset v1',
    '@EVALS_PLATFORM.STAGES.GOLDEN_DATA/invoiceiq/',
    'Initial 100 invoice baseline',
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    PARSE_JSON('{"version": "1.0", "num_records": 100}')
);
```

**Create golden records (one per test case):**
```sql
INSERT INTO GOLDEN_RECORDS VALUES (
    'invoice_001',
    'invoiceiq_validation_v1',
    'invoice_001.pdf',
    PARSE_JSON('{
        "invoice_id": "INV001",
        "relative_path": "invoice_001.pdf",
        "stage_name": "@EVALS_PLATFORM.STAGES.GOLDEN_DATA/invoiceiq/",
        "target_table": "EVALS_PLATFORM.CORE.INVOICEIQ_EVAL_RESULTS"
    }'),
    PARSE_JSON('{
        "extraction": {
            "vendor_name": "Acme Corp",
            "invoice_number": "INV-2024-001",
            "total_amount": 5000.00,
            "invoice_date": "2024-01-15",
            "purchase_order_number": "PO-12345"
        },
        "decision": {
            "ai_decision": "approve",
            "ai_reasoning": "PO found, amount matches, all validations pass"
        }
    }'),
    CURRENT_TIMESTAMP(),
    NULL
);
-- Repeat for all 100 invoices...
```

### 2. Execution Phase

**Trigger evaluation run via API:**
```bash
POST /evals/run
{
    "dataset_id": "invoiceiq_validation_v1",
    "project_endpoint": "http://invoiceiq-backend:8001/eval/invoke",
    "config": {"model_version": "v1.0"}
}
```

**Evals service orchestrates:**
```python
# 1. Create eval run record
request_id = uuid.uuid4()
INSERT INTO EVAL_RUNS (request_id, dataset_id, status, ...)

# 2. Load all golden records
golden_records = SELECT * FROM GOLDEN_RECORDS WHERE dataset_id = '...'

# 3. For each golden record:
for record in golden_records:
    # Call project eval endpoint
    response = POST to /eval/invoke {
        "request_id": request_id,
        "invoice_id": record.input_data["invoice_id"],
        ...
    }
    
    # Validate outputs
    validation = compare(response.actual_outputs, record.expected_outputs)
    
    # Store result
    INSERT INTO EVAL_RESULTS (
        request_id=request_id,
        record_id=record.record_id,
        actual_outputs=response,
        validation_results=validation,
        trulens_record_id=response.trulens_record_id
    )

# 4. Update run status
UPDATE EVAL_RUNS SET status='completed', summary_metrics={...}
```

### 3. Analysis Phase

**View run summary:**
```sql
SELECT * FROM VW_RECENT_EVAL_RUNS
WHERE project_name = 'invoiceiq'
ORDER BY run_timestamp DESC;
```

**Analyze detailed results:**
```sql
SELECT 
    file_path,
    validation_results:extraction_score::FLOAT AS extraction_score,
    validation_results:decision_accuracy::BOOLEAN AS decision_correct,
    trulens_record_id
FROM VW_EVAL_RESULTS_DETAILED
WHERE request_id = 'your-request-id'
ORDER BY extraction_score ASC;  -- Find worst performers
```

**Compare runs over time:**
```sql
SELECT 
    request_id,
    run_timestamp,
    summary_metrics:extraction_score::FLOAT AS extraction_score,
    summary_metrics:decision_score::FLOAT AS decision_score,
    summary_metrics:overall_score::FLOAT AS overall_score
FROM EVAL_RUNS
WHERE dataset_id = 'invoiceiq_validation_v1'
ORDER BY run_timestamp DESC;
```

## Planned Implementation: Multi-PR Strategy

### PR 1: Database Schema ✅ (Current)
**Branch:** `vsrinivas/initial-evals-setup`
**Status:** Complete
- Database, schemas, tables, views, stages
- Foundation for entire platform

### PR 2: InvoiceIQ Integration (Next)
**Branch:** `vsrinivas/invoiceiq-eval-integration`
**Changes:**
- Add TruLens dependencies to `invoiceiq/backend/pyproject.toml`
- Create `invoiceiq/backend/app/routers/eval.py` with `/eval/invoke` endpoint
- Wrap LangGraph with TruGraph for instrumentation
- Configure TruLens Snowflake backend
- Returns structured outputs for validation

### PR 3: Evals Service Core
**Branch:** `vsrinivas/evals-service-core`
**Changes:**
- Create `evals-service/` FastAPI application
- Dataset management APIs (CRUD for datasets and golden records)
- Validation logic (InvoiceIQ-specific validators)
- Orchestration service (calls project endpoints, validates, stores results)

### PR 4: Evals Service APIs
**Branch:** `vsrinivas/evals-service-apis`
**Changes:**
- Results querying APIs
- TruLens integration client
- Analytics and aggregation

### PR 5: Dashboard
**Branch:** `vsrinivas/evals-dashboard`
**Changes:**
- React dashboard for viewing eval runs
- Results visualization
- TruLens trace integration
- Comparison views

### PR 6: Deployment & Documentation
**Branch:** `vsrinivas/evals-deployment`
**Changes:**
- SPCS deployment configuration
- End-to-end tests
- Comprehensive documentation
- Sample golden dataset

## Key Evaluation Metrics

### InvoiceIQ Specific

**Extraction Accuracy:**
- Field-by-field comparison (vendor_name, invoice_number, etc.)
- Per-field accuracy rate
- Overall extraction score

**Decision Accuracy:**
- Correct approve/reject classification
- Reasoning quality assessment

**Performance:**
- Execution time per invoice
- Token usage
- Cost per evaluation

### TruLens Metrics (Automatic)

- **Groundedness** - Are outputs traceable to inputs?
- **Relevance** - Do responses match the request?
- **Toxicity** - Any harmful content?
- **Custom Feedback** - Project-specific evaluators

## Benefits of This Approach

### For InvoiceIQ
- Systematic validation against 100 real invoices
- Track accuracy improvements over time
- Identify edge cases and failure modes
- Confidence before production deployment

### For Organization
- Reusable infrastructure for all AI agents
- Consistent evaluation methodology
- Centralized observability
- Easy onboarding for new projects

### For Development
- Catch regressions early (CI/CD integration)
- A/B test prompt changes
- Compare model versions
- Data-driven optimization

## Getting Started

### Initial Setup (Complete)

1. Run database initialization scripts in order:

```bash
# Using Snowflake CLI
snow sql -f evals-platform/snowflake/init_database.sql -c <connection>
snow sql -f evals-platform/snowflake/init_tables.sql -c <connection>
snow sql -f evals-platform/snowflake/init_stages.sql -c <connection>
```

Or using SnowSQL:
```bash
snowsql -c <connection> -f evals-platform/snowflake/init_database.sql
snowsql -c <connection> -f evals-platform/snowflake/init_tables.sql
snowsql -c <connection> -f evals-platform/snowflake/init_stages.sql
```

2. Verify setup:
```sql
USE DATABASE EVALS_PLATFORM;
SHOW TABLES IN SCHEMA CORE;
-- Should see: GOLDEN_DATASETS, GOLDEN_RECORDS, EVAL_RUNS, EVAL_RESULTS

SHOW VIEWS IN SCHEMA CORE;
-- Should see: VW_RECENT_EVAL_RUNS, VW_EVAL_RESULTS_DETAILED

SHOW STAGES IN SCHEMA STAGES;
-- Should see: GOLDEN_DATA
```

3. Grant permissions (adjust roles as needed):
```sql
-- For evals service
GRANT USAGE ON DATABASE EVALS_PLATFORM TO ROLE evals_admin;
GRANT ALL PRIVILEGES ON ALL SCHEMAS IN DATABASE EVALS_PLATFORM TO ROLE evals_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA EVALS_PLATFORM.CORE TO ROLE evals_admin;
GRANT READ, WRITE ON STAGE EVALS_PLATFORM.STAGES.GOLDEN_DATA TO ROLE evals_admin;

-- For project services (read-only on golden data)
GRANT USAGE ON DATABASE EVALS_PLATFORM TO ROLE invoiceiq_admin;
GRANT USAGE ON SCHEMA EVALS_PLATFORM.STAGES TO ROLE invoiceiq_admin;
GRANT READ ON STAGE EVALS_PLATFORM.STAGES.GOLDEN_DATA TO ROLE invoiceiq_admin;
```

### Next Steps (After PRs 2-6)

1. Prepare golden dataset:
   - Collect 100 invoice PDFs
   - Create expected outputs for each
   - Upload to stage
   - Insert dataset and golden records

2. Deploy evals service:
   - Deploy to SPCS as shared service
   - Configure access for projects

3. Integrate InvoiceIQ:
   - Add eval endpoint
   - Configure TruLens
   - Deploy updated backend

4. Run first evaluation:
   - POST to `/evals/run` with dataset_id
   - Monitor progress
   - Analyze results

5. Iterate and improve:
   - Review failures
   - Update prompts/logic
   - Re-run evaluations
   - Track improvements

## Future Enhancements

- **Automated Scheduling** - Run evals nightly on latest code
- **CI/CD Integration** - Block merges if eval scores drop
- **Active Learning** - Promote eval failures to training data
- **Multi-Model Comparison** - A/B test different LLMs
- **Cost Optimization** - Track and optimize token usage
- **Custom Validators** - Pluggable validation functions per project
- **Alerting** - Notify on eval failures or score drops

## Technical Notes

### Why Snowflake for Evals?

- **Data locality** - Evals data lives with application data
- **VARIANT columns** - Flexible schema for any project
- **Scalability** - Handle millions of eval records
- **Query power** - SQL analytics on eval results
- **Integration** - Native with SPCS deployments

### Why TruLens?

- **LangGraph native** - Built for LangChain/LangGraph
- **Automatic instrumentation** - Minimal code changes
- **Rich metrics** - Pre-built feedback functions
- **Snowflake backend** - Stores data in our database
- **Dashboard** - Built-in visualization

### Snowflake Constraints Limitations

Snowflake regular tables don't support:
- Enforced foreign keys
- CHECK constraints
- Explicit indexes

These are handled via:
- Application-level validation
- Documented relationships in comments
- Snowflake's automatic micro-partitioning for performance

## Resources

- [TruLens Documentation](https://www.trulens.org/)
- [TruLens LangGraph Integration](https://www.trulens.org/component_guides/instrumentation/langgraph/)
- [Snowflake VARIANT Type](https://docs.snowflake.com/en/sql-reference/data-types-semistructured)
- [SPCS Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview)

## Questions or Issues?

See the detailed implementation plan in each PR or reach out to the team.

---

**Status:** Foundation complete ✅ | Next: InvoiceIQ Integration

