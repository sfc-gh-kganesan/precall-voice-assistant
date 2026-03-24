# Pattern Categories

| Category | Description | Signals |
|---|---|---|
| `auth` | Authentication, authorization, token management | OAuth, JWT, RBAC, login, session |
| `data-pipeline` | ETL/ELT, data loading, transformations | COPY INTO, stages, pipes, streams, tasks |
| `cortex-agent` | Cortex Agent definitions, tool configs | agent YAML, tool definitions, instructions |
| `cortex-search` | Cortex Search service creation and querying | CORTEX SEARCH, SEARCH_PREVIEW, embeddings |
| `streamlit-ui` | Streamlit components, layouts, state management | st., session_state, callbacks, pages |
| `spcs` | Snowpark Container Services patterns | Dockerfile, service spec, compute pool |
| `dbt` | dbt models, macros, tests, sources | config, materialized, ref(), source() |
| `error-handling` | Error handling, retry logic, logging | try/except, retry, logging, alerts |
| `testing` | Test patterns, fixtures, mocks | pytest, assert, mock, fixture |
| `data-quality` | Data validation, quality checks, DMFs | DMF, SYSTEM$CLASSIFY, constraints |
| `connection` | Snowflake connection patterns | connector, Session, connection_name |
| `deployment` | CI/CD, GitHub Actions, deployment scripts | workflow, deploy, stage, PUT |
| `document-processing` | PDF parsing, OCR, table detection, text extraction from documents | pdfplumber, bbox, extract_text, OCR, tesseract |
| `data-enrichment` | Enriching records with external data, lookups, supplier matching | enrich, lookup, PO resolution, supplier, tax |
| `llm-orchestration` | LLM agent patterns, prompt construction, model wrappers, chain orchestration | ChatOpenAI, LangGraph, agent, prompt, chain |
| `observability` | Metrics collection, usage tracking, performance monitoring | metrics, tracker, recorder, sink, rollup |
| `normalization` | Data normalization, date/currency/text formatting, value cleaning | normalize, clean, format, parse, convert |
| `api` | API endpoints, request handling, service lifecycle | FastAPI, endpoint, route, request, response |
| `duplicate-detection` | Duplicate record detection, signature building, similarity scoring | duplicate, signature, dedup, similarity, hash |
