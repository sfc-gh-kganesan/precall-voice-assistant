"""
Warehouse API endpoints for warehouse details, charts, and history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from app.dependencies import get_api_key
from app.services.warehouse_service import WarehouseService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request models for POST endpoints
class WarehouseChartRequest(BaseModel):
    """Request model for warehouse-level chart data."""

    chart_type: str = Field(
        ...,
        description="Chart type: EXECUTED_JOBS, ACTIVE_CLUSTERS, XP_RETRY_JOBS, SUCCESS_FAILURE_RATIO",
    )
    start_time: datetime = Field(..., description="Start timestamp")
    end_time: datetime = Field(..., description="End timestamp")


class ClusterChartRequest(BaseModel):
    """Request model for cluster-level chart data."""

    cluster_num: int = Field(..., description="Cluster number (1-based)", ge=1)
    chart_type: str = Field(
        ...,
        description="Chart type: JOB_QUEUE_TRANSITION, JOB_BLOCKED_TRANSITION, QUEUE_TOTAL_TIME, BLOCKED_TOTAL_TIME",
    )
    start_time: datetime = Field(..., description="Start timestamp")
    end_time: datetime = Field(..., description="End timestamp")


@router.get(
    "/warehouses/{deployment}/{account_id}/{warehouse_name}",
    response_model=Dict[str, Any],
)
async def get_warehouse_details(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get current warehouse configuration and details.

    Returns comprehensive warehouse information including:
    - Warehouse size, type, cluster configuration
    - Auto-suspend/resume settings
    - Scaling policy
    - Creation and update timestamps

    **Example:**
    ```
    GET /api/v1/warehouses/AWS_US_WEST_2/12345/COMPUTE_WH
    ```
    """
    try:
        service = WarehouseService()
        details = service.get_warehouse_details(deployment, account_id, warehouse_name)

        if details is None:
            raise HTTPException(
                status_code=404,
                detail=f"Warehouse not found: {warehouse_name} in account {account_id}",
            )

        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching warehouse details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching warehouse details: {str(e)}"
        )


@router.get(
    "/warehouses/{deployment}/{account_id}/at-query/{query_uuid}",
    response_model=Dict[str, Any],
)
async def get_warehouse_at_query_time(
    deployment: str,
    account_id: int,
    query_uuid: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get warehouse configuration at the time a specific query ran.

    This endpoint returns the warehouse settings as they were when the query was executed,
    which is useful for understanding query performance in context.

    **Example:**
    ```
    GET /api/v1/warehouses/AWS_US_WEST_2/12345/at-query/01a2b3c4-5678-90ab-cdef-1234567890ab
    ```
    """
    try:
        service = WarehouseService()
        details = service.get_warehouse_details_at_query_time(
            deployment, account_id, query_uuid
        )

        if details is None:
            raise HTTPException(
                status_code=404,
                detail=f"Warehouse configuration not found for query: {query_uuid}",
            )

        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching warehouse at query time: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching warehouse at query time: {str(e)}"
        )


@router.get(
    "/warehouses/{deployment}/{account_id}/{warehouse_name}/chart-range",
    response_model=Dict[str, Any],
)
async def get_chart_time_range(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get start and end timestamps for available chart data.

    Returns the time range for which warehouse chart data is available.
    Useful for determining valid date ranges for chart requests.

    **Example:**
    ```
    GET /api/v1/warehouses/AWS_US_WEST_2/12345/COMPUTE_WH/chart-range
    ```
    """
    try:
        service = WarehouseService()
        time_range = service.get_chart_time_range(
            deployment, account_id, warehouse_name
        )
        return time_range
    except Exception as e:
        logger.error(f"Error fetching chart time range: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching chart time range: {str(e)}"
        )


@router.get(
    "/warehouses/{deployment}/{account_id}/{warehouse_name}/changes",
    response_model=List[Dict[str, Any]],
)
async def get_warehouse_changes(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get warehouse change history (last 30 days).

    Returns list of configuration changes made to the warehouse including:
    - Event timestamp and type
    - Old and new values
    - User who made the change

    **Example:**
    ```
    GET /api/v1/warehouses/AWS_US_WEST_2/12345/COMPUTE_WH/changes
    ```
    """
    try:
        service = WarehouseService()
        changes = service.get_change_history(deployment, account_id, warehouse_name)
        return changes
    except Exception as e:
        logger.error(f"Error fetching warehouse changes: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching warehouse changes: {str(e)}"
        )


@router.post(
    "/warehouses/{deployment}/{account_id}/{warehouse_name}/warehouse-charts",
    response_model=List[Dict[str, Any]],
)
async def get_warehouse_chart_data(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    request: WarehouseChartRequest = Body(...),
    api_key: str = Depends(get_api_key),
):
    """
    Get warehouse-level chart data for the specified time range.

    Chart types:
    - EXECUTED_JOBS: Executed jobs per cluster over time
    - ACTIVE_CLUSTERS: Active cluster count over time
    - XP_RETRY_JOBS: Jobs with XP retries by cluster
    - SUCCESS_FAILURE_RATIO: Job success and failure ratios

    **Example:**
    ```
    POST /api/v1/warehouses/AWS_US_WEST_2/12345/COMPUTE_WH/warehouse-charts
    {
        "chart_type": "EXECUTED_JOBS",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-02T00:00:00Z"
    }
    ```
    """
    try:
        service = WarehouseService()
        chart_data = service.get_warehouse_chart_data(
            deployment,
            account_id,
            warehouse_name,
            request.chart_type,
            request.start_time,
            request.end_time,
        )
        return chart_data
    except ValueError as e:
        logger.error(f"Invalid chart type: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching warehouse chart data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching warehouse chart data: {str(e)}"
        )


@router.post(
    "/warehouses/{deployment}/{account_id}/{warehouse_name}/cluster-charts",
    response_model=List[Dict[str, Any]],
)
async def get_cluster_chart_data(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    request: ClusterChartRequest = Body(...),
    api_key: str = Depends(get_api_key),
):
    """
    Get cluster-level chart data for a specific cluster.

    Chart types:
    - JOB_QUEUE_TRANSITION: Job queue transitions (queued/transitioning/executing)
    - JOB_BLOCKED_TRANSITION: Job blocked transitions (blocked/transitioning/executing)
    - QUEUE_TOTAL_TIME: Queue time statistics (min/avg/max)
    - BLOCKED_TOTAL_TIME: Blocked time statistics (min/avg/max)

    **Example:**
    ```
    POST /api/v1/warehouses/AWS_US_WEST_2/12345/COMPUTE_WH/cluster-charts
    {
        "cluster_num": 1,
        "chart_type": "JOB_QUEUE_TRANSITION",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-02T00:00:00Z"
    }
    ```
    """
    try:
        service = WarehouseService()
        chart_data = service.get_cluster_chart_data(
            deployment,
            account_id,
            warehouse_name,
            request.cluster_num,
            request.chart_type,
            request.start_time,
            request.end_time,
        )
        return chart_data
    except ValueError as e:
        logger.error(f"Invalid chart type: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching cluster chart data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching cluster chart data: {str(e)}"
        )


@router.get(
    "/warehouses/{deployment}/{account_id}/{warehouse_name}/overlays",
    response_model=List[Dict[str, Any]],
)
async def get_event_overlays(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    start_time: datetime = Query(..., description="Start timestamp"),
    end_time: datetime = Query(..., description="End timestamp"),
    api_key: str = Depends(get_api_key),
):
    """
    Get warehouse events for chart overlays within a time range.

    Returns events (configuration changes, parameter overrides, etc.) that can be
    displayed as overlays on warehouse charts.

    **Example:**
    ```
    GET /api/v1/warehouses/AWS_US_WEST_2/12345/COMPUTE_WH/overlays?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
    ```
    """
    try:
        service = WarehouseService()
        events = service.get_event_overlays(
            deployment,
            account_id,
            warehouse_name,
            start_time,
            end_time,
        )
        return events
    except Exception as e:
        logger.error(f"Error fetching event overlays: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching event overlays: {str(e)}"
        )
