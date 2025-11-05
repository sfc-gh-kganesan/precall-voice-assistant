"""
TSW (Troubleshooting Wizard) API endpoints for diagnostic operations.

This module provides 7 TSW diagnostic endpoints:
1. UDF Analysis
2. Query Compilation
3. Iceberg Tables
4. Query Locks
5. Incident Errors
6. User Authentication (SAML/OAUTH)
7. RBAC Analysis
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_api_key
from app.services.tsw_service import TswService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Endpoint 1: UDF Analysis
# ============================================================================


@router.get("/udf/{query_id}", response_model=Dict[str, Any])
async def analyze_udf(query_id: str, api_key: str = Depends(get_api_key)):
    """
    Analyze UDF (User-Defined Function) usage for a query.

    Returns:
    - query_metadata: Basic query information
    - udf_analysis: UDF analysis results from stored procedure
    - table_objects: Tables accessed by the query

    **Example:**
    ```
    GET /api/v1/tsw/udf/01234567-89ab-cdef-0123-456789abcdef
    ```
    """
    try:
        service = TswService()
        result = service.analyze_udf(query_id)

        if not result:
            raise HTTPException(
                status_code=404, detail=f"No UDF data found for query: {query_id}"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing UDF for query {query_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Endpoint 2: Query Compilation Analysis
# ============================================================================


@router.get("/compilation/{case_number}", response_model=Dict[str, Any])
async def analyze_compilation(case_number: str, api_key: str = Depends(get_api_key)):
    """
    Analyze query compilation issues for a case.

    Returns:
    - query_metadata: Metadata for all queries in the case
    - queries_with_issues: Queries with high compilation time
    - package_data: Pre-computed data if available

    **Example:**
    ```
    GET /api/v1/tsw/compilation/00012345
    ```
    """
    try:
        service = TswService()
        result = service.analyze_compilation(case_number)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No compilation data found for case: {case_number}",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing compilation for case {case_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Endpoint 3: Iceberg Table Diagnostics
# ============================================================================


@router.get("/iceberg/{query_id}", response_model=Dict[str, Any])
async def analyze_iceberg(
    query_id: str,
    case_number: Optional[str] = Query(
        None, description="Optional case number for package data lookup"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Analyze Iceberg table issues for a query.

    Returns:
    - table_name: Iceberg table name
    - package_data: Pre-computed data if available (requires case_number)

    **Example:**
    ```
    GET /api/v1/tsw/iceberg/01234567-89ab-cdef-0123-456789abcdef?case_number=00012345
    ```
    """
    try:
        service = TswService()
        result = service.analyze_iceberg(query_id, case_number)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No Iceberg table data found for query: {query_id}",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing Iceberg for query {query_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Endpoint 4: Query Locks Analysis
# ============================================================================


@router.get(
    "/locks/{deployment}/{account_id}/{query_id}", response_model=Dict[str, Any]
)
async def analyze_locks(
    deployment: str,
    account_id: int,
    query_id: str,
    case_number: Optional[str] = Query(
        None, description="Optional case number for package data lookup"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Analyze query lock issues.

    Returns:
    - locking_queries: Queries that were blocking this query
    - package_data: Pre-computed data if available (requires case_number)

    **Example:**
    ```
    GET /api/v1/tsw/locks/AWS_US_WEST_2/12345/01234567-89ab-cdef-0123-456789abcdef?case_number=00012345
    ```
    """
    try:
        service = TswService()
        result = service.analyze_locks(query_id, deployment, account_id, case_number)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error analyzing locks for query {query_id} in deployment {deployment}: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Endpoint 5: Incident Errors Analysis
# ============================================================================


@router.get("/incidents/{case_number}", response_model=Dict[str, Any])
async def analyze_incidents(case_number: str, api_key: str = Depends(get_api_key)):
    """
    Analyze incident errors for a case.

    Returns:
    - query_ids: List of query IDs with incident errors
    - package_data: Pre-computed data for each query if available

    **Example:**
    ```
    GET /api/v1/tsw/incidents/00012345
    ```
    """
    try:
        service = TswService()
        result = service.analyze_incidents(case_number)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing incidents for case {case_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Endpoint 6: User Authentication (SAML/OAUTH) Analysis
# ============================================================================


@router.get("/auth/{deployment}/{account_id}", response_model=Dict[str, Any])
async def analyze_auth(
    deployment: str,
    account_id: int,
    case_number: Optional[str] = Query(
        None, description="Optional case number for package data lookup"
    ),
    start_time: Optional[datetime] = Query(
        None, description="Start time for log queries"
    ),
    end_time: Optional[datetime] = Query(None, description="End time for log queries"),
    api_key: str = Depends(get_api_key),
):
    """
    Analyze user authentication issues (SAML/OAUTH).

    Returns:
    - saml_integrations: SAML integration details
    - oauth_integrations: OAUTH integration details
    - saml_logs: SAML authentication logs (if time range provided)
    - oauth_logs: OAUTH authentication logs (if time range provided)
    - package_data: Pre-computed data if available (requires case_number)

    **Example:**
    ```
    GET /api/v1/tsw/auth/AWS_US_WEST_2/12345?case_number=00012345&start_time=2024-01-01T00:00:00&end_time=2024-01-02T00:00:00
    ```
    """
    try:
        service = TswService()
        result = service.analyze_auth(
            deployment, account_id, case_number, start_time, end_time
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No auth data found for deployment {deployment}, account {account_id}",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error analyzing auth for deployment {deployment}, account {account_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Endpoint 7: RBAC Analysis
# ============================================================================


@router.get("/rbac/{deployment}/{account_id}/{query_id}", response_model=Dict[str, Any])
async def analyze_rbac(
    deployment: str,
    account_id: int,
    query_id: str,
    api_key: str = Depends(get_api_key),
):
    """
    Analyze RBAC (Role-Based Access Control) issues for a query.

    Returns:
    - query_details: Query metadata including error details
    - candidate_securables: Securables that might be causing the issue
    - user_data: User information (if available)
    - role_data: Role information (if available)

    **Example:**
    ```
    GET /api/v1/tsw/rbac/AWS_US_WEST_2/12345/01234567-89ab-cdef-0123-456789abcdef
    ```
    """
    try:
        service = TswService()
        result = service.analyze_rbac(query_id, deployment, account_id)

        if not result:
            raise HTTPException(
                status_code=404, detail=f"No RBAC data found for query: {query_id}"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error analyzing RBAC for query {query_id} in deployment {deployment}: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))
