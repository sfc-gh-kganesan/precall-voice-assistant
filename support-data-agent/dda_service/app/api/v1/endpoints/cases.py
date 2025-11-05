"""
Case API Endpoints

Provides REST API endpoints for case-related operations.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
import logging

from app.services.case_service import CaseService

logger = logging.getLogger(__name__)

router = APIRouter()
case_service = CaseService()


@router.get("/{case_number}")
def get_case(
    case_number: str,
) -> dict:
    """
    Get case metadata.

    Returns comprehensive metadata for a specific Salesforce case.

    **Path Parameters:**
    - **case_number**: Salesforce case number (e.g., "01087579")

    **Returns:**
    - Case metadata including status, priority, dates, owner, account info

    **Example:**
    ```bash
    curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/cases/01087579
    ```
    """
    try:
        result = case_service.get_case_metadata(case_number)

        if result is None:
            raise HTTPException(
                status_code=404, detail=f"Case not found: {case_number}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching case {case_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_number}/queries")
def get_case_queries(
    case_number: str,
) -> dict:
    """
    Get all queries associated with a case.

    Returns list of queries linked to this case through various mappings
    (DDA, adhoc relations, query metadata).

    **Path Parameters:**
    - **case_number**: Salesforce case number

    **Returns:**
    - List of queries with metadata (SQL, timestamps, errors, warehouse, user, etc.)
    - Query count

    **Example:**
    ```bash
    curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/cases/01087579/queries
    ```
    """
    try:
        queries = case_service.get_case_queries(case_number)
        count = case_service.get_case_query_count(case_number)

        return {"case_number": case_number, "query_count": count, "queries": queries}

    except Exception as e:
        logger.error(f"Error fetching queries for case {case_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/cases")
def search_cases(
    status: Optional[str] = Query(None, description="Case status (Open, Closed, etc.)"),
    is_closed: Optional[bool] = Query(None, description="Filter by closed status"),
    functional_area: Optional[str] = Query(
        None, description="Functional area (Performance, Security, etc.)"
    ),
    start_date: Optional[datetime] = Query(
        None, description="Filter cases created after this date"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter cases created before this date"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
) -> dict:
    """
    Search cases by various criteria.

    **Query Parameters:**
    - **status**: Case status filter
    - **is_closed**: Boolean closed status
    - **functional_area**: Functional area filter
    - **start_date**: Created after date (ISO format)
    - **end_date**: Created before date (ISO format)
    - **limit**: Max results (1-1000, default 100)

    **Returns:**
    - List of cases matching criteria
    - Result count

    **Example:**
    ```bash
    curl -H "X-API-Key: your_key" \
      "http://localhost:8000/api/v1/cases/search/cases?is_closed=false&limit=50"
    ```
    """
    try:
        results = case_service.search_cases(
            status=status,
            is_closed=is_closed,
            functional_area=functional_area,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        return {"count": len(results), "cases": results}

    except Exception as e:
        logger.error(f"Error searching cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))
