"""
JIRA API Endpoints

Provides REST API endpoints for JIRA ticket search operations.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Path
import logging

from app.services.jira_service import JiraService
from app.integrations.jira.models import (
    JiraSearchResponse,
    JiraTicket,
    SimilarTicketsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()
jira_service = JiraService()


@router.get("/search/query/{query_id}", response_model=JiraSearchResponse)
def search_by_query_id(
    query_id: str = Path(..., description="Snowflake query ID"),
    max_results: Optional[int] = Query(
        None, ge=1, le=100, description="Max results (1-100)"
    ),
) -> JiraSearchResponse:
    """
    Search JIRA tickets by query ID.

    Searches for the query ID in ticket descriptions and summaries.
    """
    try:
        return jira_service.search_by_query_id(query_id, max_results=max_results)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching JIRA by query_id {query_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/account/{account_locator}", response_model=JiraSearchResponse)
def search_by_account(
    account_locator: str = Path(..., description="Account locator"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    max_results: Optional[int] = Query(
        None, ge=1, le=100, description="Max results (1-100)"
    ),
) -> JiraSearchResponse:
    """
    Search JIRA tickets by account locator.

    Searches the account locator custom field.
    """
    try:
        return jira_service.search_by_account_locator(
            account_locator, status=status, max_results=max_results
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching JIRA by account {account_locator}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/case/{case_number}", response_model=JiraSearchResponse)
def search_by_case(
    case_number: str = Path(..., description="Salesforce case number"),
    max_results: Optional[int] = Query(
        None, ge=1, le=100, description="Max results (1-100)"
    ),
) -> JiraSearchResponse:
    """
    Search JIRA tickets by case number.

    Searches for case number references in summary, description, and comments.
    """
    try:
        return jira_service.search_by_case_number(case_number, max_results=max_results)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching JIRA by case {case_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/similar", response_model=SimilarTicketsResponse)
def search_similar(
    error_message: Optional[str] = Query(
        None, description="Error message to search for"
    ),
    component: Optional[str] = Query(None, description="Component name"),
    deployment: Optional[str] = Query(None, description="Deployment name"),
    area: Optional[str] = Query(None, description="JIRA area"),
    days: int = Query(30, ge=1, le=90, description="Search last N days (1-90)"),
    similarity_threshold: float = Query(
        0.5, ge=0.0, le=1.0, description="Minimum similarity score (0-1)"
    ),
    max_results: Optional[int] = Query(
        None, ge=1, le=100, description="Max results (1-100)"
    ),
) -> SimilarTicketsResponse:
    """
    Find similar JIRA tickets based on error message and metadata.

    Uses similarity scoring to find tickets that match the search criteria.
    At least one search criterion must be provided.
    """
    # Validate at least one criterion provided
    if not any([error_message, component, deployment, area]):
        raise HTTPException(
            status_code=400,
            detail="At least one search criterion must be provided",
        )

    try:
        return jira_service.find_similar_tickets(
            error_message=error_message,
            component=component,
            deployment=deployment,
            area=area,
            days=days,
            similarity_threshold=similarity_threshold,
            max_results=max_results,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching for similar JIRA tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticket_key}", response_model=JiraTicket)
def get_ticket(
    ticket_key: str = Path(..., description="JIRA ticket key (e.g., SNOW-12345)"),
) -> JiraTicket:
    """
    Get a single JIRA ticket by key.
    """
    try:
        return jira_service.get_ticket(ticket_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching JIRA ticket {ticket_key}: {e}")
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
            raise HTTPException(
                status_code=404, detail=f"Ticket {ticket_key} not found"
            )
        raise HTTPException(status_code=500, detail=str(e))
