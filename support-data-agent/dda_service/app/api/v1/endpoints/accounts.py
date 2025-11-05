"""
Account API endpoints for account search, metadata, warehouses, cases, and more.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_api_key
from app.services.account_service import AccountService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/accounts/search", response_model=List[Dict[str, Any]])
async def search_accounts(
    search_query: str = Query(
        ..., description="Search term for account locator, alias, or ID"
    ),
    deployment: Optional[str] = Query(None, description="Optional deployment filter"),
    api_key: str = Depends(get_api_key),
):
    """
    Search for accounts by partial match on locator, alias, or account ID.

    Results are ranked with exact matches first, followed by partial matches.

    **Example:**
    ```
    POST /api/v1/accounts/search?search_query=snowhouse
    ```
    """
    try:
        service = AccountService()
        results = service.search_accounts(search_query, deployment)
        return results
    except Exception as e:
        logger.error(f"Error searching accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error searching accounts: {str(e)}"
        )


@router.get("/accounts/{deployment}/{locator}", response_model=Dict[str, Any])
async def get_account_metadata(
    deployment: str,
    locator: str,
    api_key: str = Depends(get_api_key),
):
    """
    Get comprehensive account metadata including service level, status, type, and region.

    Returns detailed information about:
    - Basic account info (name, alias, account_id)
    - Service level and account status
    - Version and release groups
    - Load balancer type
    - Cloud provider and region details

    **Example:**
    ```
    GET /api/v1/accounts/AWS_US_WEST_2/myaccount
    ```
    """
    try:
        service = AccountService()
        metadata = service.get_account_metadata(deployment, locator)

        if metadata is None:
            raise HTTPException(
                status_code=404,
                detail=f"Account not found: {locator} in deployment {deployment}",
            )

        return metadata
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching account metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching account metadata: {str(e)}"
        )


@router.get(
    "/accounts/{deployment}/{account_id}/releases", response_model=List[Dict[str, Any]]
)
async def get_release_history(
    deployment: str,
    account_id: int,
    limit: int = Query(
        100, description="Maximum number of releases to return", ge=1, le=500
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get release version history for an account.

    Returns a list of releases with version numbers and timestamps, ordered by most recent first.

    **Example:**
    ```
    GET /api/v1/accounts/AWS_US_WEST_2/12345/releases?limit=50
    ```
    """
    try:
        service = AccountService()
        releases = service.get_release_history(deployment, account_id, limit)
        return releases
    except Exception as e:
        logger.error(f"Error fetching release history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching release history: {str(e)}"
        )


@router.get(
    "/accounts/{deployment}/{account_id}/warehouses",
    response_model=List[Dict[str, Any]],
)
async def get_account_warehouses(
    deployment: str,
    account_id: int,
    api_key: str = Depends(get_api_key),
):
    """
    Get list of warehouses for an account.

    Returns warehouse information including:
    - Warehouse name, size, and type
    - Provisioning and creation timestamps
    - Load data availability

    **Example:**
    ```
    GET /api/v1/accounts/AWS_US_WEST_2/12345/warehouses
    ```
    """
    try:
        service = AccountService()
        warehouses = service.get_account_warehouses(deployment, account_id)
        return warehouses
    except Exception as e:
        logger.error(f"Error fetching warehouses: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching warehouses: {str(e)}"
        )


@router.get(
    "/accounts/{deployment}/{locator}/cases", response_model=List[Dict[str, Any]]
)
async def get_open_cases(
    deployment: str,
    locator: str,
    alias: str = Query(..., description="Account alias"),
    api_key: str = Depends(get_api_key),
):
    """
    Get open Salesforce cases for an account.

    Returns list of open cases with status, category, subcategory, and subject.

    **Example:**
    ```
    GET /api/v1/accounts/AWS_US_WEST_2/myaccount/cases?alias=MYACCOUNT
    ```
    """
    try:
        service = AccountService()
        cases = service.get_open_cases(deployment, locator, alias)
        return cases
    except Exception as e:
        logger.error(f"Error fetching open cases: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching open cases: {str(e)}"
        )


@router.get(
    "/accounts/{deployment}/{locator}/queries", response_model=List[Dict[str, Any]]
)
async def get_account_queries(
    deployment: str,
    locator: str,
    limit: int = Query(
        100, description="Maximum number of queries to return", ge=1, le=500
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get queries executed on this account.

    Returns list of queries with query_id, case_number, timestamp, and SQL hash.
    Ordered by most recent first.

    **Example:**
    ```
    GET /api/v1/accounts/AWS_US_WEST_2/myaccount/queries?limit=50
    ```
    """
    try:
        service = AccountService()
        queries = service.get_account_queries(deployment, locator, limit)
        return queries
    except Exception as e:
        logger.error(f"Error fetching account queries: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching account queries: {str(e)}"
        )


@router.get(
    "/accounts/{deployment}/{account_id}/environment", response_model=Dict[str, str]
)
async def get_account_environment(
    deployment: str,
    account_id: int,
    api_key: str = Depends(get_api_key),
):
    """
    Get account environment type (prod/dev/test/etc).

    Returns the environment classification for the account.

    **Example:**
    ```
    GET /api/v1/accounts/AWS_US_WEST_2/12345/environment
    ```
    """
    try:
        service = AccountService()
        environment = service.get_account_environment(deployment, account_id)

        if environment is None:
            raise HTTPException(
                status_code=404,
                detail=f"Environment not found for account_id: {account_id}",
            )

        return {"environment": environment}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching account environment: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching account environment: {str(e)}"
        )
