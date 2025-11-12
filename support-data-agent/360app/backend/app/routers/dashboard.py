from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from ..schemas.dashboard import KPIsResponse, ProductMetrics, TopicMetrics
from ..services import analytics

router = APIRouter()


@router.get("/kpis", response_model=KPIsResponse)
async def get_kpis(
    period: str = Query(..., pattern="^(week|month|custom)$"),
    startDate: str | None = None,
    endDate: str | None = None,
    products: Annotated[list[str] | None, Query()] = None,
    topics: Annotated[list[str] | None, Query()] = None,
    categories: Annotated[list[str] | None, Query()] = None,
):
    try:
        kpis = await run_in_threadpool(analytics.get_kpis, period, startDate, endDate, products, topics, categories)
        return KPIsResponse(**kpis)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/products", response_model=list[ProductMetrics])
async def get_products(
    period: str = Query(..., pattern="^(week|month|custom)$"),
    startDate: str | None = None,
    endDate: str | None = None,
    products: Annotated[list[str] | None, Query()] = None,
    topics: Annotated[list[str] | None, Query()] = None,
    categories: Annotated[list[str] | None, Query()] = None,
):
    try:
        product_metrics = await run_in_threadpool(
            analytics.get_product_metrics,
            period,
            startDate,
            endDate,
            products,
            topics,
            categories,
        )
        return product_metrics
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/topics", response_model=list[TopicMetrics])
async def get_topics(
    period: str = Query(..., pattern="^(week|month|custom)$"),
    startDate: str | None = None,
    endDate: str | None = None,
    products: Annotated[list[str] | None, Query()] = None,
    topics: Annotated[list[str] | None, Query()] = None,
    categories: Annotated[list[str] | None, Query()] = None,
):
    try:
        topic_metrics = await run_in_threadpool(
            analytics.get_topic_metrics,
            period,
            startDate,
            endDate,
            products,
            topics,
            categories,
        )
        return topic_metrics
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/products/performance")
async def get_product_performance(
    period: str = Query(..., pattern="^(week|month|custom)$"),
    startDate: str | None = None,
    endDate: str | None = None,
):
    """
    Get product performance trends showing top and bottom performers.

    Returns top 3 and bottom 3 performers for:
    - Case volume change
    - Resolution time change
    - Resolution rate change
    """
    try:
        performance_data = await run_in_threadpool(
            analytics.get_product_performance,
            period,
            startDate,
            endDate,
        )
        return performance_data
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/topics/performance")
async def get_topic_performance(
    period: str = Query(..., pattern="^(week|month|custom)$"),
    startDate: str | None = None,
    endDate: str | None = None,
):
    """
    Get topic performance trends showing top and bottom performers.

    Returns top 3 and bottom 3 performers for:
    - Case volume change
    - Resolution time change
    - Resolution rate change
    """
    try:
        performance_data = await run_in_threadpool(
            analytics.get_topic_performance,
            period,
            startDate,
            endDate,
        )
        return performance_data
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/categories")
async def get_categories(
    period: str = Query(..., pattern="^(week|month|custom)$"),
    startDate: str | None = None,
    endDate: str | None = None,
):
    """
    Get category-level metrics by aggregating all products within each category.

    Returns list of categories with:
    - Total cases
    - Case change and change percentage
    - Average resolution time
    - Resolution rate
    - Product count
    """
    try:
        category_metrics = await run_in_threadpool(
            analytics.get_category_metrics,
            period,
            startDate,
            endDate,
        )
        return category_metrics
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/categories/{category}/subcategories")
async def get_subcategories(
    category: str,
    period: str = Query(..., pattern="^(week|month|custom)$"),
    startDate: str | None = None,
    endDate: str | None = None,
):
    """
    Get subcategory-level metrics for a specific category.

    Returns list of subcategories within the specified category with:
    - Total cases
    - Case change and change percentage
    - Average resolution time
    - Resolution rate
    """
    try:
        subcategory_metrics = await run_in_threadpool(
            analytics.get_subcategory_metrics,
            period,
            category,
            startDate,
            endDate,
        )
        return subcategory_metrics
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
