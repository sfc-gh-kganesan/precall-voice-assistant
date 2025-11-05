"""
Query endpoints for comprehensive query analysis.
Implements all query-related operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Query as QueryParam

from app.dependencies import get_api_key
from app.services.query_service import QueryService

# Create router
router = APIRouter()


@router.get("/{query_id}")
async def get_query_metadata(
    query_id: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get comprehensive query metadata including all duration breakdowns.

    Returns 18+ duration metrics, query statistics, error information,
    and execution details.
    """
    service = QueryService()
    result = service.get_query_metadata(query_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query with ID '{query_id}' not found",
        )

    return {"data": result}


@router.get("/{query_id}/historical-runs")
async def get_historical_runs(
    query_id: str,
    limit: int = QueryParam(
        default=1000,
        le=10000,
        description="Maximum number of historical runs to return",
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get historical runs of queries with the same SQL hash.

    Returns up to `limit` historical query executions that share the same
    SQL fingerprint, useful for performance comparison analysis.
    """
    service = QueryService()
    result = service.get_historical_runs(query_id, limit)

    return {"data": result}


@router.get("/{query_id}/concurrent")
async def get_concurrent_queries(
    query_id: str,
    cluster_number: Optional[int] = QueryParam(
        default=None, description="Filter by cluster number"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get queries that ran concurrently in the same warehouse.

    Returns queries that were executing at the same time in the same
    warehouse, useful for analyzing contention and performance impact.
    """
    service = QueryService()
    result = service.get_concurrent_queries(query_id, cluster_number)

    return {"data": result}


@router.get("/{query_id}/logs/gs")
async def get_gs_logs(
    query_id: str,
    limit: int = QueryParam(
        default=1000, le=10000, description="Maximum number of log entries"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get Global Services (GS) logs for a query.

    Returns GS-layer logs which include metadata service operations,
    authentication, and query planning activities.
    """
    service = QueryService()
    result = service.get_gs_logs(query_id, limit)

    return {"data": result}


@router.get("/{query_id}/logs/xp")
async def get_xp_logs(
    query_id: str,
    limit: int = QueryParam(
        default=1000, le=10000, description="Maximum number of log entries"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get Execution Platform (XP) logs for a query.

    Returns XP-layer logs which include query execution details,
    virtual warehouse operations, and compute resource usage.
    """
    service = QueryService()
    result = service.get_xp_logs(query_id, limit)

    return {"data": result}


@router.get("/{query_id}/parameters")
async def get_query_parameters(
    query_id: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get non-default parameters for a query.

    Returns session and account parameters that differ from default values,
    which can significantly impact query behavior and performance.
    """
    service = QueryService()
    result = service.get_parameters(query_id)

    return {"data": result}


@router.get("/{query_id}/incidents")
async def get_query_incidents(
    query_id: str,
    limit: int = QueryParam(
        default=5, le=20, description="Maximum number of incidents"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get incidents from Crash Manager for a query.

    Returns incidents and crashes related to this query execution,
    useful for identifying systemic issues or bugs.
    """
    service = QueryService()
    result = service.get_incidents(query_id, limit)

    return {"data": result}


@router.get("/{query_id}/parent-child")
async def get_parent_child_tree(
    query_id: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get parent-child query execution tree.

    Returns the hierarchical relationship between parent and child queries,
    useful for analyzing stored procedure and complex query execution flows.
    """
    service = QueryService()
    result = service.get_parent_child_tree(query_id)

    return {"data": result}


@router.get("/{query_id}/processing-status")
async def get_processing_status(
    query_id: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get DDA pipeline processing status (0-100%).

    Returns the current processing status of the query through the
    DDA data pipeline, indicating data availability.
    """
    service = QueryService()
    result = service.get_processing_status(query_id)

    return {"data": result}


@router.post("/adhoc-process")
async def trigger_adhoc_process(
    query_id: str = QueryParam(..., description="Query ID to process"),
    case_number: str = QueryParam(..., description="Associated case number"),
    api_key: str = Depends(get_api_key),
):
    """
    Trigger adhoc DDA pipeline processing.

    Initiates on-demand processing of a query through the DDA pipeline,
    useful for urgent case analysis or when automatic processing hasn't completed.
    """
    # Extract user email from API key context if available
    # For MVP, we'll use a placeholder
    user_email = "api_user@snowflake.com"

    service = QueryService()
    result = service.trigger_adhoc_process(query_id, case_number, user_email)

    return {"data": result}


@router.post("/compare")
async def compare_queries(
    query_id_1: str = QueryParam(..., description="First query ID"),
    query_id_2: str = QueryParam(..., description="Second query ID"),
    api_key: str = Depends(get_api_key),
):
    """
    Compare two queries (metadata, parameters, performance).

    Returns a detailed comparison of two query executions, highlighting
    differences in performance, resource usage, and configuration.
    """
    service = QueryService()
    result = service.compare_queries(query_id_1, query_id_2)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=result["error"]
        )

    return {"data": result}
