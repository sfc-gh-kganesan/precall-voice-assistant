from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from ..schemas.usage import (
    BiggestMoversResponse,
    TopAccount,
    UsageMetrics,
    UsageTrendPoint,
)
from ..services import usage

router = APIRouter()


@router.get("/credits-timeline", response_model=list[UsageTrendPoint])
async def get_credits_timeline(
    date_range: str | None = None,
    certified_organization_type: str = "Customer",
    certified_deployment: str = "All",
    certified_salesforce_account_id: str | None = None,
    certified_salesforce_account_name: str | None = None,
    include_coda: bool = False,
):
    """
    Get credits consumption timeline with rolling 7-day average.

    Returns time series of daily credits with rolling average.
    """
    try:
        timeline = await run_in_threadpool(
            usage.get_credits_timeline,
            date_range,
            certified_organization_type,
            certified_deployment,
            certified_salesforce_account_id,
            certified_salesforce_account_name,
            include_coda,
        )
        return timeline
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/top-accounts", response_model=list[TopAccount])
async def get_top_accounts(
    certified_organization_type: str = "Customer",
    certified_deployment: str = "All",
    certified_salesforce_account_name: str | None = None,
):
    """
    Get top accounts ranked by total active serving rows.

    Returns list of accounts with usage metrics sorted by capacity.
    """
    try:
        accounts = await run_in_threadpool(
            usage.get_top_accounts_by_serving_rows,
            certified_organization_type,
            certified_deployment,
            certified_salesforce_account_name,
        )
        return accounts
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/biggest-movers", response_model=BiggestMoversResponse)
async def get_biggest_movers(
    period: str = Query("7d", pattern="^(7d|30d)$"),
    certified_organization_type: str = "Customer",
    certified_deployment: str = "All",
    certified_salesforce_account_id: str | None = None,
    certified_salesforce_account_name: str | None = None,
    include_coda: bool = False,
):
    """
    Get top 5 gainers and top 5 decliners by credit consumption change.

    Currently only supports 7d period.
    """
    try:
        if period == "7d":
            movers = await run_in_threadpool(
                usage.get_biggest_movers_7d,
                certified_organization_type,
                certified_deployment,
                certified_salesforce_account_id,
                certified_salesforce_account_name,
                include_coda,
            )
        else:
            # 30d period not yet implemented
            movers = {"gainers": [], "decliners": []}

        return BiggestMoversResponse(**movers)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/metrics-summary", response_model=UsageMetrics)
async def get_usage_metrics_summary():
    """
    Get high-level usage metrics summary for KPI cards.

    Returns total credits, active accounts, and trend data.
    """
    try:
        metrics = await run_in_threadpool(usage.get_usage_metrics_summary)
        return UsageMetrics(**metrics)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/case-counts")
async def get_case_counts(product_name: str, days: int = 30):
    """
    Get case counts by account for a specific product.

    Returns mapping of account names to case counts for the last N days.
    """
    try:
        counts = await run_in_threadpool(usage.get_case_counts_by_account, product_name, days)
        return counts
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
