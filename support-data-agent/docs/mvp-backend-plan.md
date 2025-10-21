# Backend MVP Implementation Plan

## Overview

This MVP assumes:
- Raw CASES table already exists in Snowflake with AI-generated fields populated
- No Docker containerization required
- No authentication/authorization
- No admin UI or configuration management
- Focus: Connect existing data to frontend dashboard

**Goal**: Get the frontend dashboard displaying real data from Snowflake in the shortest time possible.

---

## Phase 1: Foundation (4 hours)

### 1.1 Project Setup (1 hour)
**Location**: `backend/`

Create minimal FastAPI project structure:
```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Snowflake connection settings
│   ├── dependencies.py      # Snowpark session dependency
│   │
│   ├── routers/
│   │   └── dashboard.py     # Dashboard endpoints only
│   │
│   ├── services/
│   │   └── analytics.py     # Query logic for dashboard
│   │
│   └── models/
│       └── responses.py     # Pydantic response models
│
├── requirements.txt
└── README.md
```

**Tasks**:
- [ ] Create directory structure
- [ ] Create `requirements.txt` with minimal dependencies:
  ```
  fastapi==0.104.1
  uvicorn[standard]==0.24.0
  snowflake-snowpark-python==1.9.0
  pydantic==2.5.0
  python-dotenv==1.0.0
  ```
- [ ] Document required environment variables for Snowflake credentials
- [ ] Create basic `main.py` with FastAPI app initialization

### 1.2 Snowflake Connection (1 hour)
**Location**: `backend/app/config.py`, `backend/app/dependencies.py`

**Tasks**:
- [ ] Create `config.py` with Pydantic settings:
  ```python
  from pydantic_settings import BaseSettings

  class Settings(BaseSettings):
      snowflake_account: str
      snowflake_user: str
      snowflake_password: str
      snowflake_warehouse: str
      snowflake_database: str
      snowflake_schema: str

      class Config:
          env_file = ".env"
  ```
- [ ] Create `dependencies.py` with session factory:
  ```python
  from snowflake.snowpark import Session
  from functools import lru_cache

  @lru_cache()
  def get_session():
      return Session.builder.configs({...}).create()

  async def get_snowpark_session() -> Session:
      return get_session()
  ```
- [ ] Test connection with simple query: `SELECT COUNT(*) FROM CASES`

### 1.3 Response Models (1 hour)
**Location**: `backend/app/models/responses.py`

**Tasks**:
- [ ] Create Pydantic models matching frontend TypeScript interfaces:
  - `KPIMetric`
  - `ProductMetrics`
  - `TopicMetrics`
  - `PerformanceItem`
  - `PerformanceData`
- [ ] Ensure models match frontend expectations from `frontend/types/index.ts`

### 1.4 Basic Health Check (1 hour)
**Location**: `backend/app/main.py`

**Tasks**:
- [ ] Add `/health` endpoint that returns `{"status": "healthy"}`
- [ ] Add `/ready` endpoint that tests Snowflake connectivity
- [ ] Test locally: `uvicorn app.main:app --reload`
- [ ] Verify health endpoints work

---

## Phase 2: Dashboard Read APIs (8 hours)

### 2.1 KPIs Endpoint (2 hours)
**Location**: `backend/app/routers/dashboard.py`, `backend/app/services/analytics.py`

**Endpoint**: `GET /api/v1/dashboard/kpis`

**Query Logic** (in `analytics.py`):
```sql
-- Platform-wide KPIs with period comparison
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
SELECT * FROM current_period CROSS JOIN previous_period
```

**Tasks**:
- [ ] Implement `get_kpis()` method in `AnalyticsService`
- [ ] Handle period filters (week, month, custom)
- [ ] Calculate change metrics (absolute change, percentage, change type)
- [ ] Return structured `KPIMetric` objects
- [ ] Test with Postman/curl

### 2.2 Product Performance Endpoint (3 hours)
**Location**: `backend/app/services/analytics.py`

**Endpoint**: `GET /api/v1/dashboard/products/performance`

**Query Logic**:
```sql
-- Product metrics with week-over-week comparison
WITH current_period AS (
  SELECT
    GENERATED_PRODUCT as product,
    COUNT(*) as total_cases,
    AVG(RESOLUTION_TIME_HOURS) as avg_resolution_time,
    SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as resolution_rate
  FROM CASES
  WHERE CREATED_AT >= :start_date AND CREATED_AT < :end_date
  GROUP BY GENERATED_PRODUCT
),
previous_period AS (
  SELECT
    GENERATED_PRODUCT as product,
    COUNT(*) as total_cases,
    AVG(RESOLUTION_TIME_HOURS) as avg_resolution_time,
    SUM(CASE WHEN STATUS = 'Closed' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as resolution_rate
  FROM CASES
  WHERE CREATED_AT >= :prev_start_date AND CREATED_AT < :prev_end_date
  GROUP BY GENERATED_PRODUCT
)
SELECT
  c.product,
  c.total_cases as current_cases,
  p.total_cases as previous_cases,
  c.total_cases - p.total_cases as change,
  ((c.total_cases - p.total_cases)::FLOAT / p.total_cases * 100) as change_percentage,
  c.avg_resolution_time as current_resolution_time,
  p.avg_resolution_time as previous_resolution_time,
  c.resolution_rate as current_resolution_rate,
  p.resolution_rate as previous_resolution_rate
FROM current_period c
LEFT JOIN previous_period p ON c.product = p.product
ORDER BY ABS(c.total_cases - p.total_cases) DESC
```

**Tasks**:
- [ ] Implement `get_product_performance()` method
- [ ] Calculate metrics for: case volume, resolution time, resolution rate
- [ ] Identify top 3 increases and top 3 decreases for each metric
- [ ] Return `PerformanceData` structure matching frontend expectations
- [ ] Test with different time periods

### 2.3 Topic Performance Endpoint (3 hours)
**Location**: `backend/app/services/analytics.py`

**Endpoint**: `GET /api/v1/dashboard/topics/performance`

**Query Logic**: Similar to product performance but grouped by `GENERATED_TOPIC`

**Tasks**:
- [ ] Implement `get_topic_performance()` method
- [ ] Calculate metrics for: case volume, resolution time, resolution rate
- [ ] Identify top 3 increases and top 3 decreases for each metric
- [ ] Return `PerformanceData` structure
- [ ] Test with different time periods

---

## Phase 3: Testing & Integration (4 hours)

### 3.1 Local Testing (2 hours)

**Tasks**:
- [ ] Test all endpoints with real Snowflake data
- [ ] Verify response formats match frontend TypeScript interfaces
- [ ] Test filter parameters (week, month, custom date ranges)
- [ ] Test edge cases (no data, single record, etc.)
- [ ] Document any discrepancies between backend responses and frontend expectations

### 3.2 Frontend Integration (2 hours)

**Tasks**:
- [ ] Update `frontend/services/api.ts` to call real backend endpoints
- [ ] Replace mock implementations with actual HTTP calls
- [ ] Add error handling for failed API requests
- [ ] Test frontend dashboard with real backend data
- [ ] Verify KPI cards, product performance, and topic performance sections render correctly

---

## Phase 4: Optional Enhancements (if time allows)

### 4.1 Basic Caching (1 hour)
- [ ] Add simple in-memory TTL cache (5 min) for frequently accessed queries
- [ ] Use `cachetools` library

### 4.2 CORS Configuration (30 min)
- [ ] Add CORS middleware to allow frontend origin
- [ ] Configure allowed origins, methods, headers

### 4.3 Logging (30 min)
- [ ] Add structured logging with `structlog`
- [ ] Log query execution times
- [ ] Log errors with stack traces

---

## Total Estimated Time: 16 hours (2 days)

---

## Key Simplifications for MVP

1. **No Authentication**: All endpoints are public
2. **No Docker**: Run with `uvicorn` directly
3. **No Configuration Management**: Assumes CASES table exists and is populated
4. **No Admin UI**: No database discovery, no field mapping, no generation jobs
5. **No Pre-aggregation**: Query CASES table directly (optimize later if needed)
6. **No Chat Interface**: Focus on dashboard analytics only
7. **No Rate Limiting**: Add later if needed
8. **No Deployment Automation**: Run locally for MVP

---

## Success Criteria

- [ ] Backend runs locally with `uvicorn app.main:app --reload`
- [ ] `/health` and `/ready` endpoints return 200 OK
- [ ] `/api/v1/dashboard/kpis` returns real KPI metrics from CASES table
- [ ] `/api/v1/dashboard/products/performance` returns product performance data
- [ ] `/api/v1/dashboard/topics/performance` returns topic performance data
- [ ] Frontend dashboard displays real data from backend
- [ ] All API responses match frontend TypeScript interfaces
- [ ] Dashboard loads in under 2 seconds with real data

---

## Running the MVP

```bash
# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run backend
uvicorn app.main:app --reload --port 8000

# Frontend setup (in another terminal)
cd frontend
npm install
npm run dev

# Open browser
http://localhost:3000/dashboard
```

---

## Next Steps After MVP

Once the MVP is working:
1. Add pre-aggregated PRODUCTS and TOPICS tables for better performance
2. Add simple authentication (JWT)
3. Add configuration management for multi-table support
4. Dockerize for easier deployment
5. Add comprehensive error handling and logging
6. Add unit and integration tests
7. Deploy to staging environment
