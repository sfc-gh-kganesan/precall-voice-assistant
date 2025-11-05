# DDA Service - Demo Script

## Overview
This document provides simplified demo scenarios for presenting the DDA Service capabilities. Each scenario includes only the customer-provided information needed to start the investigation.

---

## Demo 1: Warehouse Cost & Provisioning Analysis

**User Story:** As a support engineer, I need to investigate warehouse cost discrepancies to identify unexpected charges and optimize customer spend.

**Customer Information:**
- **Case Number:** 01087579
- **Customer:** UDW_US_PRD (Account: GUA88493)
- **Severity:** Severity-2 (High impact, business operational)
- **Cloud/Region:** AWS / US-EAST-1

**Problem Description:**
Customer reports significant difference between actual cost incurred vs compute cost for their DMP project warehouses.

**Warehouses Involved:**
- UDW_DMP_DEFAULT_WH_PROD
- UDW_DMP_POC_WH_PROD_LARGE
- UDW_DMP_PP_WH_4XLARGE_PROD
- UDW_DMP_PP_WH_LARGE_PROD
- UDW_DMP_PP_WH_MEDIUM_PROD
- UDW_DMP_PP_WH_PROD
- UDW_DMP_PP_WH_PROD_2XL_GEN2
- UDW_DMP_PP_WH_PROD_2XLARGE
- UDW_DMP_PP_WH_SMALL_PROD
- UDW_DMP_PP_WH_XL_PROD
- UDW_DMP_PP_WH_XLARGE_PROD
- UDW_DMP_PP_WH_XSMALL_PROD
- UDW_DMP_PP_WH_XXXLARGE_PROD

**Investigation Goal:**
Determine why actual costs don't match expected compute costs and identify optimization opportunities.

---

## Demo 2: Query Incident Analysis

**User Story:** As a support engineer, I need to analyze query incidents to determine root cause and provide resolution guidance.

**Customer Information:**
- **Case Number:** 01176219
- **Customer:** DW_PROD (SIGNIFYHEALTH_DMT_PROD)
- **Severity:** Severity-4 (Low impact)
- **Query ID:** 01c02675-0a0d-015c-00e6-ed048446782b

**Problem Description:**
A SELECT DISTINCT query began failing on one column of a view but not others. The column has a high percentage of nulls (34M of 52M rows).

**Customer Observations:**
- Adding a predicate did not resolve the issue
- A CTE that first selects non-nulls and then applies DISTINCT succeeds
- Query fails with an internal error incident

**Investigation Goal:**
Determine why the SELECT DISTINCT operation fails and whether this is expected behavior.

---

## Demo 3: Query Performance Analysis - Disk Spilling

**User Story:** As a support engineer, I need to diagnose performance discrepancies between similar queries to identify resource bottlenecks.

**Customer Information:**
- **Case Number:** 01176342
- **Customer:** GPN_CERT (Global Payments)
- **Severity:** Severity-3 (Medium to low impact)
- **Cloud/Region:** GCP / US-CENTRAL1

**Problem Description:**
Two similar queries have drastically different performance. One query spills to disk and remote storage heavily, while the other does not.

**Query Information:**
- **Fast Query ID:** 01c02092-0006-ee74-0004-0afa0117a89e
- **Slow Query ID:** 01c0208e-0006-ef4a-0004-0afa0117b082

**Customer Observations:**
- Queries are similar in structure
- Cannot understand why one spills to remote storage while the other doesn't
- Significant performance difference between the two

**Investigation Goal:**
Identify why one query spills to disk/remote while the similar query doesn't and provide optimization recommendations.

---

## Demo 4: Query Slowness - Transaction Lock Investigation

**User Story:** As a support engineer, I need to identify transaction lock chains that block query execution to resolve performance issues.

**Customer Information:**
- **Case Number:** 01172497
- **Query ID:** 01c00d3d-0a0c-f195-0196-2e015312a02b
- **Deployment:** azeastus2prod
- **Account ID:** 103982

**Problem Description:**
Customer's DELETE query for data retention cleanup is extremely slow (3+ hours) and eventually fails.

**Query Information:**
```sql
DELETE FROM SCAMP_DB.RPGW_USER_CELL_SUMM
WHERE conn_time <= dateadd(days, (-1)*370, current_date())
```

**Customer Observations:**
- Query takes over 3 hours before failing
- Error: "Stored procedure child job is cancelled upon parent jobs termination or completion"
- Data retention cleanup is not completing

**Investigation Goal:**
Determine if transaction locks are causing the slowness and identify the blocking query to resolve the issue.

---

## Demo Flow Guidelines

For each demo:

1. **Start with the case** - Understand the customer context and severity
2. **Gather queries** - Identify all relevant queries in the case
3. **Analyze diagnostics** - Use appropriate TSW endpoints (locks, incidents, compilation, etc.)
4. **Identify root cause** - Explain what the data reveals
5. **Provide recommendations** - Offer actionable next steps

---

*Last Updated: 2025-11-03*
*DDA Service Version: v1.0*
