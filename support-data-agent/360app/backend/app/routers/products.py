from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from ..services import analytics

router = APIRouter()


@router.get("/benchmarks")
async def get_product_benchmarks(
    period: str = Query(..., pattern="^(week|month|custom)$"),
    category: str | None = None,
    subcategory: str | None = None,
    productId: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
):
    """
    Get benchmarking data showing top/bottom performers and averages.

    Args:
        period: Time period ('week', 'month', 'custom')
        category: Optional category filter
        subcategory: Optional subcategory filter
        productId: Optional specific product to benchmark against
        startDate: Start date for custom period (ISO format)
        endDate: End date for custom period (ISO format)

    Returns:
        Dictionary with:
        - scope: Category/subcategory name or "All Products"
        - average: Average metrics (cases, time, rate)
        - topPerformer: Product with highest case volume
        - bottomPerformer: Product with lowest case volume
        - bestTimePerformer: Product with fastest resolution time
        - bestRatePerformer: Product with highest resolution rate
        - yourProduct: Metrics for specific product if productId provided
    """
    try:
        benchmarks = await run_in_threadpool(
            analytics.get_product_benchmarks,
            period,
            category,
            subcategory,
            productId,
            startDate,
            endDate,
        )
        return benchmarks
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/search")
async def search_products(
    query: str = Query(..., min_length=1),
    category: str | None = None,
    subcategory: str | None = None,
):
    """
    Search products by name with optional category/subcategory filters.

    Args:
        query: Search query string
        category: Optional category filter
        subcategory: Optional subcategory filter

    Returns:
        List of matching products (up to 50) with:
        - productId
        - productName
        - productCategory
        - productSubcategory
    """
    try:
        products = await run_in_threadpool(
            analytics.search_products,
            query,
            category,
            subcategory,
        )
        return products
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_benchmark_context(product_id: str, period: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """
    Get benchmark context for a specific product showing comparisons to subcategory and category averages.

    Args:
        product_id: Product ID
        period: Time period ('week', 'month', 'custom')
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)

    Returns:
        Dictionary with your product metrics and comparisons to subcategory/category averages
    """
    # Get all products to find the specific product and calculate averages
    all_products = analytics.get_product_metrics(period, start_date, end_date)

    # Find the specific product
    your_product = next((p for p in all_products if p["productId"] == product_id), None)

    if not your_product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    category = your_product["productCategory"]
    subcategory = your_product.get("productSubcategory")

    # Get product metrics
    your_metrics = {
        "cases": your_product["metrics"]["totalCases"]["value"],
        "avgTime": your_product["metrics"]["avgCaseLife"]["value"],
        "resolutionRate": your_product["metrics"]["resolutionRate"]["value"],
    }

    result = {
        "yourProduct": {
            "productId": your_product["productId"],
            "productName": your_product["productName"],
            "category": category,
            "subcategory": subcategory,
            "metrics": your_metrics,
        }
    }

    def calculate_comparison(your_value: float, avg_value: float, metric_type: str):
        """Calculate comparison with direction and status."""
        if avg_value == 0:
            return {"delta": 0, "direction": "neutral", "status": "neutral"}

        delta_pct = ((your_value - avg_value) / avg_value) * 100

        if metric_type == "cases":
            # More cases = worse
            direction = "higher" if delta_pct > 0 else ("lower" if delta_pct < 0 else "neutral")
            status = "worse" if delta_pct > 0 else ("better" if delta_pct < 0 else "neutral")
        elif metric_type == "time":
            # Higher time = worse
            direction = "higher" if delta_pct > 0 else ("lower" if delta_pct < 0 else "neutral")
            status = "worse" if delta_pct > 0 else ("better" if delta_pct < 0 else "neutral")
        else:  # rate
            # Higher rate = better
            direction = "higher" if delta_pct > 0 else ("lower" if delta_pct < 0 else "neutral")
            status = "better" if delta_pct > 0 else ("worse" if delta_pct < 0 else "neutral")

        return {"delta": round(delta_pct, 1), "direction": direction, "status": status}

    # Calculate subcategory average if subcategory exists
    if subcategory:
        subcategory_products = [p for p in all_products if p.get("productSubcategory") == subcategory and p["productId"] != product_id]

        if subcategory_products:
            subcat_avg_cases = sum(p["metrics"]["totalCases"]["value"] for p in subcategory_products) / len(subcategory_products)
            subcat_avg_time = sum(p["metrics"]["avgCaseLife"]["value"] for p in subcategory_products) / len(subcategory_products)
            subcat_avg_rate = sum(p["metrics"]["resolutionRate"]["value"] for p in subcategory_products) / len(subcategory_products)

            result["subcategoryAverage"] = {
                "name": subcategory,
                "metrics": {
                    "cases": round(subcat_avg_cases, 1),
                    "avgTime": round(subcat_avg_time, 1),
                    "resolutionRate": round(subcat_avg_rate, 1),
                },
                "comparison": {
                    "cases": calculate_comparison(your_metrics["cases"], subcat_avg_cases, "cases"),
                    "avgTime": calculate_comparison(your_metrics["avgTime"], subcat_avg_time, "time"),
                    "resolutionRate": calculate_comparison(your_metrics["resolutionRate"], subcat_avg_rate, "rate"),
                },
            }

    # Calculate category average
    category_products = [p for p in all_products if p["productCategory"] == category and p["productId"] != product_id]

    if category_products:
        cat_avg_cases = sum(p["metrics"]["totalCases"]["value"] for p in category_products) / len(category_products)
        cat_avg_time = sum(p["metrics"]["avgCaseLife"]["value"] for p in category_products) / len(category_products)
        cat_avg_rate = sum(p["metrics"]["resolutionRate"]["value"] for p in category_products) / len(category_products)

        result["categoryAverage"] = {
            "name": category,
            "metrics": {
                "cases": round(cat_avg_cases, 1),
                "avgTime": round(cat_avg_time, 1),
                "resolutionRate": round(cat_avg_rate, 1),
            },
            "comparison": {
                "cases": calculate_comparison(your_metrics["cases"], cat_avg_cases, "cases"),
                "avgTime": calculate_comparison(your_metrics["avgTime"], cat_avg_time, "time"),
                "resolutionRate": calculate_comparison(your_metrics["resolutionRate"], cat_avg_rate, "rate"),
            },
        }

    return result


@router.get("/{product_id}/benchmark-context")
async def get_product_benchmark_context(
    product_id: str,
    period: str = Query("week", pattern="^(week|month|custom)$"),
    startDate: str | None = None,
    endDate: str | None = None,
):
    """
    Get benchmark context for a specific product showing comparisons to subcategory and category averages.

    Args:
        product_id: Product ID
        period: Time period (week, month, custom)
        startDate: Start date for custom period (ISO format)
        endDate: End date for custom period (ISO format)

    Returns:
        Benchmark context with your product metrics and comparisons to subcategory/category averages
    """
    try:
        return await run_in_threadpool(_get_benchmark_context, product_id, period, startDate, endDate)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
