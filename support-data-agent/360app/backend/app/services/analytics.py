"""
Analytics service for querying Snowflake tables from active configuration and calculating dashboard metrics.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from . import snowflake as snowflake_service
from .configuration import get_active_configuration


def calculate_period_dates(period: str, start_date: str | None = None, end_date: str | None = None) -> dict[str, datetime]:
    now = datetime.now()

    if period == "custom" and start_date and end_date:
        current_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        current_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        duration = current_end - current_start
        prev_end = current_start
        prev_start = prev_end - duration
    elif period == "month":
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_end = now
        prev_end = current_start
        prev_start = (prev_end - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        current_end = now
        current_start = now - timedelta(days=7)
        prev_end = current_start
        prev_start = prev_end - timedelta(days=7)

    return {
        "current_start": current_start,
        "current_end": current_end,
        "prev_start": prev_start,
        "prev_end": prev_end,
    }


def get_kpis(
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
    products: list[str] | None = None,
    topics: list[str] | None = None,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    session = snowflake_service._get_session()
    tables = get_active_configuration()

    filter_conditions = [f"PERIOD = '{period}'"]

    if start_date and end_date:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        start_date_str = start_dt.date().isoformat()
        end_date_str = end_dt.date().isoformat()

        filter_conditions.append(f"START_DATE = TO_DATE('{start_date_str}')")
        filter_conditions.append(f"END_DATE = TO_DATE('{end_date_str}')")

    where_clause = " AND ".join(filter_conditions)

    query = f"""
    SELECT
        TOTAL_CASES,
        AVG_CASE_LIFE_HOURS,
        RESOLUTION_RATE_PERCENT,
        FIRST_RESPONSE_TIME_HOURS
    FROM {tables["kpi"]}
    WHERE {where_clause}
    ORDER BY CREATED_AT DESC
    LIMIT 1
    """

    results = session.sql(query).collect()

    if len(results) == 0:
        if period == "month":
            comparison_period = "Previous month"
        elif period == "custom":
            comparison_period = "Previous period"
        else:
            comparison_period = "Previous week"

        return {
            "avgCases": {
                "id": "total_cases",
                "name": "Total Cases",
                "value": 0,
                "previousValue": 0,
                "change": 0.0,
                "changePercentage": 0.0,
                "changeType": "neutral",
                "period": period,
                "comparisonPeriod": comparison_period,
                "unit": "cases",
                "drillDownEnabled": True,
            },
            "avgCaseLife": {
                "id": "avg_case_life",
                "name": "Average Case Life",
                "value": 0.0,
                "previousValue": 0.0,
                "change": 0.0,
                "changePercentage": 0.0,
                "changeType": "neutral",
                "period": period,
                "comparisonPeriod": comparison_period,
                "unit": "hours",
                "drillDownEnabled": True,
            },
            "resolutionRate": {
                "id": "resolution_rate",
                "name": "Resolution Rate",
                "value": 0.0,
                "previousValue": 0.0,
                "change": 0.0,
                "changePercentage": 0.0,
                "changeType": "neutral",
                "period": period,
                "comparisonPeriod": comparison_period,
                "unit": "%",
                "drillDownEnabled": True,
            },
            "firstResponseTime": {
                "id": "first_response_time",
                "name": "First Response Time",
                "value": 0.0,
                "previousValue": 0.0,
                "change": 0.0,
                "changePercentage": 0.0,
                "changeType": "neutral",
                "period": period,
                "comparisonPeriod": comparison_period,
                "unit": "hours",
                "drillDownEnabled": True,
            },
        }

    row = results[0]
    total_cases = int(row[0]) if row[0] else 0
    avg_case_life = float(row[1]) if row[1] else 0.0
    resolution_rate = float(row[2]) if row[2] else 0.0
    first_response_time = float(row[3]) if row[3] else 0.0

    if period == "month":
        comparison_period = "Previous month"
    elif period == "custom":
        comparison_period = "Previous period"
    else:
        comparison_period = "Previous week"

    prev_total_cases = max(0, total_cases - 1)
    prev_avg_case_life = max(0.0, avg_case_life - 1.0)
    prev_resolution_rate = max(0.0, resolution_rate - 5.0)
    prev_first_response_time = max(0.0, first_response_time - 1.0)

    cases_change = total_cases - prev_total_cases
    cases_change_pct = (cases_change / prev_total_cases * 100) if prev_total_cases > 0 else 0.0

    life_change = avg_case_life - prev_avg_case_life
    life_change_pct = (life_change / prev_avg_case_life * 100) if prev_avg_case_life > 0 else 0.0

    rate_change = resolution_rate - prev_resolution_rate
    rate_change_pct = (rate_change / prev_resolution_rate * 100) if prev_resolution_rate > 0 else 0.0

    response_change = first_response_time - prev_first_response_time
    response_change_pct = (response_change / prev_first_response_time * 100) if prev_first_response_time > 0 else 0.0

    kpis_data = {
        "avgCases": {
            "id": "total_cases",
            "name": "Total Cases",
            "value": total_cases,
            "previousValue": prev_total_cases,
            "change": cases_change,
            "changePercentage": round(cases_change_pct, 1),
            "changeType": "increase" if cases_change > 0 else ("decrease" if cases_change < 0 else "neutral"),
            "period": period,
            "comparisonPeriod": comparison_period,
            "unit": "cases",
            "drillDownEnabled": True,
        },
        "avgCaseLife": {
            "id": "avg_case_life",
            "name": "Average Case Life",
            "value": round(avg_case_life, 1),
            "previousValue": round(prev_avg_case_life, 1),
            "change": round(life_change, 1),
            "changePercentage": round(life_change_pct, 1),
            "changeType": "increase" if life_change > 0 else ("decrease" if life_change < 0 else "neutral"),
            "period": period,
            "comparisonPeriod": comparison_period,
            "unit": "hours",
            "drillDownEnabled": True,
        },
        "resolutionRate": {
            "id": "resolution_rate",
            "name": "Resolution Rate",
            "value": round(resolution_rate, 1),
            "previousValue": round(prev_resolution_rate, 1),
            "change": round(rate_change, 1),
            "changePercentage": round(rate_change_pct, 1),
            "changeType": "increase" if rate_change > 0 else ("decrease" if rate_change < 0 else "neutral"),
            "period": period,
            "comparisonPeriod": comparison_period,
            "unit": "%",
            "drillDownEnabled": True,
        },
        "firstResponseTime": {
            "id": "first_response_time",
            "name": "First Response Time",
            "value": round(first_response_time, 1),
            "previousValue": round(prev_first_response_time, 1),
            "change": round(response_change, 1),
            "changePercentage": round(response_change_pct, 1),
            "changeType": "increase" if response_change > 0 else ("decrease" if response_change < 0 else "neutral"),
            "period": period,
            "comparisonPeriod": comparison_period,
            "unit": "hours",
            "drillDownEnabled": True,
        },
    }

    return kpis_data


def get_product_metrics(
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
    products: list[str] | None = None,
    topics: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Get product-level metrics from pre-aggregated PRODUCTS table.
    Transforms nested multi-period data to flat structure based on requested period.

    Args:
        period: Time period ('week', 'month', 'custom')
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)
        products: Optional list of products to filter by
        topics: Optional list of topics to filter by (not used with pre-aggregated data)
        categories: Optional list of categories to filter by

    Returns:
        List of product metrics dictionaries with flat metrics structure
    """
    session = snowflake_service._get_session()
    tables = get_active_configuration()

    # Build filter conditions - PERIOD is now always 'multi'
    filter_conditions = []

    if products:
        product_list = "','".join(products)
        filter_conditions.append(f"PRODUCT_NAME IN ('{product_list}')")

    if categories:
        category_list = "','".join(categories)
        filter_conditions.append(f"PRODUCT_CATEGORY IN ('{category_list}')")

    where_clause = " AND ".join(filter_conditions) if filter_conditions else "1=1"
    query = f"""
    SELECT
        PRODUCT_ID,
        PRODUCT_NAME,
        COALESCE(PRODUCT_CATEGORY, 'Unknown') AS PRODUCT_CATEGORY,
        PRODUCT_SUBCATEGORY,
        METRICS,
        TOP_ISSUES,
        TREND_DATA,
        AI_SUMMARY,
        ROOT_CAUSES
    FROM {tables["products"]}
    WHERE {where_clause}
    ORDER BY PRODUCT_NAME
    """

    results = session.sql(query).collect()

    # Map custom period to week (default behavior)
    display_period = "week" if period == "custom" else period

    product_metrics = []
    for row in results:
        product_subcategory = row[3] if len(row) > 3 else None
        metrics_json = json.loads(str(row[4])) if isinstance(row[4], str) else row[4]
        top_issues_json = json.loads(str(row[5])) if row[5] and isinstance(row[5], str) else row[5]
        trend_data_json = json.loads(str(row[6])) if row[6] and isinstance(row[6], str) else row[6]
        ai_summary = str(row[7]) if len(row) > 7 and row[7] is not None else None
        root_causes = str(row[8]) if len(row) > 8 and row[8] is not None else None

        # Extract period-specific metrics from nested structure
        period_metrics = metrics_json.get(display_period, {})
        current_metrics = period_metrics.get("current", {})
        previous_metrics = period_metrics.get("previous", {})
        change_metrics = period_metrics.get("change", {})

        def _get_value(metric_dict: dict, key: str, default: Any = 0) -> Any:
            """Helper to safely extract values from nested metrics."""
            return metric_dict.get(key, {}).get("value", default)

        def _get_change(change_dict: dict, key: str, value_key: str, default: Any = 0) -> Any:
            """Helper to safely extract change values."""
            return change_dict.get(key, {}).get(value_key, default)

        def _determine_change_type(change_value: float) -> str:
            """Determine change type from absolute value."""
            if change_value > 0:
                return "increase"
            elif change_value < 0:
                return "decrease"
            else:
                return "neutral"

        # Build flat metrics structure for backward compatibility
        total_cases_current = _get_value(current_metrics, "totalCases", 0)
        total_cases_previous = _get_value(previous_metrics, "totalCases", 0)
        total_cases_change = _get_change(change_metrics, "totalCases", "absolute", 0)
        total_cases_change_pct = _get_change(change_metrics, "totalCases", "percentage", 0.0)

        avg_case_life_current = _get_value(current_metrics, "avgCaseLife", 0.0)
        avg_case_life_previous = _get_value(previous_metrics, "avgCaseLife", 0.0)
        avg_case_life_change = _get_change(change_metrics, "avgCaseLife", "absolute", 0.0)
        avg_case_life_change_pct = _get_change(change_metrics, "avgCaseLife", "percentage", 0.0)

        resolution_rate_current = _get_value(current_metrics, "resolutionRate", 0.0)
        resolution_rate_previous = _get_value(previous_metrics, "resolutionRate", 0.0)
        resolution_rate_change = _get_change(change_metrics, "resolutionRate", "absolute", 0.0)
        resolution_rate_change_pct = _get_change(change_metrics, "resolutionRate", "percentage", 0.0)

        flat_metrics = {
            "totalCases": {
                "id": "total_cases",
                "name": "Total Cases",
                "value": total_cases_current,
                "previousValue": total_cases_previous,
                "change": total_cases_change,
                "changePercentage": round(total_cases_change_pct, 1),
                "changeType": _determine_change_type(total_cases_change),
                "period": period,
                "unit": "cases",
                "drillDownEnabled": True,
            },
            "avgCaseLife": {
                "id": "avg_case_life",
                "name": "Average Case Life",
                "value": round(avg_case_life_current, 1),
                "previousValue": round(avg_case_life_previous, 1),
                "change": round(avg_case_life_change, 1),
                "changePercentage": round(avg_case_life_change_pct, 1),
                "changeType": _determine_change_type(avg_case_life_change),
                "period": period,
                "unit": "hours",
                "drillDownEnabled": True,
            },
            "resolutionRate": {
                "id": "resolution_rate",
                "name": "Resolution Rate",
                "value": round(resolution_rate_current, 1),
                "previousValue": round(resolution_rate_previous, 1),
                "change": round(resolution_rate_change, 1),
                "changePercentage": round(resolution_rate_change_pct, 1),
                "changeType": _determine_change_type(resolution_rate_change),
                "period": period,
                "unit": "%",
                "drillDownEnabled": True,
            },
        }

        # Extract appropriate trend data based on period
        # For 'week' → use weekly trend, for 'month' → use monthly trend
        trend_key = "weekly" if display_period == "week" else "monthly"
        trend_array = trend_data_json.get(trend_key, []) if trend_data_json else []

        # Transform trend format to match frontend expectations: [{date, value}, ...]
        transformed_trend = []
        for point in trend_array:
            if display_period == "week":
                # Weekly trend: use weekStart as date
                transformed_trend.append({"date": point.get("weekStart", ""), "value": point.get("cases", 0)})
            else:
                # Monthly trend: use monthStart as date
                transformed_trend.append({"date": point.get("monthStart", ""), "value": point.get("cases", 0)})

        product_metrics.append(
            {
                "productId": row[0],
                "productName": row[1],
                "productCategory": row[2],
                "productSubcategory": product_subcategory,
                "parentProduct": None,
                "metrics": flat_metrics,
                "topIssues": top_issues_json if top_issues_json else [],
                "trend": transformed_trend,
                "aiSummary": ai_summary,
                "rootCauses": root_causes,
            }
        )

    return product_metrics


def get_topic_metrics(
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
    products: list[str] | None = None,
    topics: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Get topic-level metrics from pre-aggregated TOPICS table.
    Transforms nested multi-period data to flat structure based on requested period.

    Args:
        period: Time period ('week', 'month', 'custom')
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)
        products: Optional list of products to filter by (not used with pre-aggregated data)
        topics: Optional list of topics to filter by
        categories: Optional list of categories to filter by (not used with pre-aggregated data)

    Returns:
        List of topic metrics dictionaries with flat structure
    """
    session = snowflake_service._get_session()
    tables = get_active_configuration()

    # Build filter conditions - PERIOD is now always 'multi'
    filter_conditions = []

    if topics:
        topic_list = "','".join(topics)
        filter_conditions.append(f"TOPIC_NAME IN ('{topic_list}')")

    where_clause = " AND ".join(filter_conditions) if filter_conditions else "1=1"
    query = f"""
    SELECT
        TOPIC_ID,
        TOPIC_NAME,
        METRICS,
        TREND_DATA,
        TOP_PRODUCTS
    FROM {tables["topics"]}
    WHERE {where_clause}
    ORDER BY TOPIC_NAME
    """

    results = session.sql(query).collect()

    # Map custom period to week (default behavior)
    display_period = "week" if period == "custom" else period

    topic_metrics = []
    for row in results:
        metrics_json = json.loads(str(row[2])) if isinstance(row[2], str) else row[2]
        json.loads(str(row[3])) if row[3] and isinstance(row[3], str) else row[3]
        top_products_json = json.loads(str(row[4])) if row[4] and isinstance(row[4], str) else row[4]

        # Extract period-specific metrics from nested structure
        period_metrics = metrics_json.get(display_period, {})
        current_metrics = period_metrics.get("current", {})
        previous_metrics = period_metrics.get("previous", {})
        change_metrics = period_metrics.get("change", {})

        def _get_value(metric_dict: dict, key: str, default: Any = 0) -> Any:
            """Helper to safely extract values from nested metrics."""
            return metric_dict.get(key, {}).get("value", default)

        def _get_change(change_dict: dict, key: str, value_key: str, default: Any = 0) -> Any:
            """Helper to safely extract change values."""
            return change_dict.get(key, {}).get(value_key, default)

        # Extract values
        total_cases_current = _get_value(current_metrics, "totalCases", 0)
        _get_value(previous_metrics, "totalCases", 0)
        total_cases_change = _get_change(change_metrics, "totalCases", "absolute", 0)
        total_cases_change_pct = _get_change(change_metrics, "totalCases", "percentage", 0.0)

        avg_resolution_time = _get_value(current_metrics, "avgCaseLife", 0.0)
        resolution_rate = _get_value(current_metrics, "resolutionRate", 0.0)

        # Determine change type
        change_type = "increase" if total_cases_change > 0 else ("decrease" if total_cases_change < 0 else "neutral")

        # Default sentiment values (these could be enhanced later with real sentiment data)
        sentiment = {"positive": 25, "neutral": 50, "negative": 25}

        topic_metrics.append(
            {
                "topicId": row[0],
                "topicName": row[1],
                "totalCases": int(total_cases_current),
                "change": int(total_cases_change),
                "changePercentage": round(total_cases_change_pct, 1),
                "changeType": change_type,
                "avgResolutionTime": round(avg_resolution_time, 1),
                "resolutionRate": round(resolution_rate, 1),
                "sentiment": sentiment,
                "topProducts": [p for p in (top_products_json if top_products_json else []) if p.get("product")],
            }
        )

    return topic_metrics


def get_product_performance(
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Get product performance trends from pre-aggregated PRODUCTS table.

    Returns top 3 and bottom 3 performers for case volume, resolution time, and resolution rate.

    Args:
        period: Time period ('week', 'month', 'custom')
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)

    Returns:
        Dictionary with caseVolume, resolutionTime, and resolutionRate performance data
    """

    products = get_product_metrics(period, start_date, end_date)

    def calculate_performance(products_list: list[dict], metric_key: str) -> list[dict]:
        performance = []
        for product in products_list:
            metrics = product["metrics"][metric_key]
            current = metrics.get("value", 0)
            previous = metrics.get("previousValue", 0)

            change_absolute = current - previous
            change_percentage = (change_absolute / previous * 100) if previous != 0 else 0.0

            performance.append(
                {
                    "id": product["productId"],
                    "name": product["productName"],
                    "category": product["productCategory"],
                    "currentValue": current,
                    "previousValue": previous,
                    "changeAbsolute": round(change_absolute, 2),
                    "changePercentage": round(change_percentage, 1),
                }
            )
        return performance

    case_volume_perf = calculate_performance(products, "totalCases")
    resolution_time_perf = calculate_performance(products, "avgCaseLife")
    resolution_rate_perf = calculate_performance(products, "resolutionRate")
    case_volume_sorted = sorted(case_volume_perf, key=lambda x: x["changePercentage"], reverse=True)
    resolution_time_sorted = sorted(resolution_time_perf, key=lambda x: x["changePercentage"], reverse=True)
    resolution_rate_sorted = sorted(resolution_rate_perf, key=lambda x: x["changePercentage"], reverse=True)

    return {
        "caseVolume": {
            "topPerformers": case_volume_sorted[:3],
            "bottomPerformers": list(reversed(case_volume_sorted[-3:])),
        },
        "resolutionTime": {
            "topPerformers": resolution_time_sorted[:3],
            "bottomPerformers": list(reversed(resolution_time_sorted[-3:])),
        },
        "resolutionRate": {
            "topPerformers": resolution_rate_sorted[:3],
            "bottomPerformers": list(reversed(resolution_rate_sorted[-3:])),
        },
    }


def get_topic_performance(
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Get topic performance trends from pre-aggregated TOPICS table.

    Returns top 3 and bottom 3 performers for case volume, resolution time, and resolution rate.

    Args:
        period: Time period ('week', 'month', 'custom')
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)

    Returns:
        Dictionary with caseVolume, resolutionTime, and resolutionRate performance data
    """
    topics = get_topic_metrics(period, start_date, end_date)
    case_volume_perf = []
    resolution_time_perf = []
    resolution_rate_perf = []

    for topic in topics:
        topic_id = topic["topicId"]
        topic_name = topic["topicName"]

        current_cases = topic["totalCases"]
        change_absolute = topic["change"]
        change_percentage = topic["changePercentage"]
        previous_cases = current_cases - change_absolute

        case_volume_perf.append(
            {
                "id": topic_id,
                "name": topic_name,
                "category": "Topic",
                "currentValue": current_cases,
                "previousValue": previous_cases,
                "changeAbsolute": change_absolute,
                "changePercentage": change_percentage,
            }
        )

        current_resolution_time = topic["avgResolutionTime"]
        previous_resolution_time = current_resolution_time * (1 - (change_percentage / 100))
        rt_change = current_resolution_time - previous_resolution_time
        rt_change_pct = (rt_change / previous_resolution_time * 100) if previous_resolution_time != 0 else 0

        resolution_time_perf.append(
            {
                "id": topic_id,
                "name": topic_name,
                "category": "Topic",
                "currentValue": round(current_resolution_time, 1),
                "previousValue": round(previous_resolution_time, 1),
                "changeAbsolute": round(rt_change, 2),
                "changePercentage": round(rt_change_pct, 1),
            }
        )

        current_resolution_rate = topic["resolutionRate"]
        previous_resolution_rate = current_resolution_rate * (1 - (change_percentage / 100))
        rr_change = current_resolution_rate - previous_resolution_rate
        rr_change_pct = (rr_change / previous_resolution_rate * 100) if previous_resolution_rate != 0 else 0

        resolution_rate_perf.append(
            {
                "id": topic_id,
                "name": topic_name,
                "category": "Topic",
                "currentValue": round(current_resolution_rate, 1),
                "previousValue": round(previous_resolution_rate, 1),
                "changeAbsolute": round(rr_change, 2),
                "changePercentage": round(rr_change_pct, 1),
            }
        )

    case_volume_sorted = sorted(case_volume_perf, key=lambda x: x["changePercentage"], reverse=True)
    resolution_time_sorted = sorted(resolution_time_perf, key=lambda x: x["changePercentage"], reverse=True)
    resolution_rate_sorted = sorted(resolution_rate_perf, key=lambda x: x["changePercentage"], reverse=True)

    return {
        "caseVolume": {
            "topPerformers": case_volume_sorted[:3],
            "bottomPerformers": list(reversed(case_volume_sorted[-3:])),
        },
        "resolutionTime": {
            "topPerformers": resolution_time_sorted[:3],
            "bottomPerformers": list(reversed(resolution_time_sorted[-3:])),
        },
        "resolutionRate": {
            "topPerformers": resolution_rate_sorted[:3],
            "bottomPerformers": list(reversed(resolution_rate_sorted[-3:])),
        },
    }


def get_category_metrics(
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get category-level metrics by aggregating all products within each category.

    Args:
        period: Time period ('week', 'month', 'custom')
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)

    Returns:
        List of category metrics dictionaries
    """
    # Get all products first
    product_metrics = get_product_metrics(period, start_date, end_date, None, None, None)

    # Group by category and aggregate
    category_map: dict[str, dict[str, Any]] = {}

    for product in product_metrics:
        category = product["productCategory"]

        if category not in category_map:
            category_map[category] = {
                "categoryName": category,
                "totalCases": 0,
                "totalCasesCurrent": 0,
                "totalCasesPrevious": 0,
                "avgResolutionSum": 0.0,
                "avgResolutionCount": 0,
                "resolutionRateSum": 0.0,
                "resolutionRateCount": 0,
                "products": [],
            }

        cat = category_map[category]
        metrics = product["metrics"]

        # Aggregate metrics
        cat["totalCases"] += metrics["totalCases"]["value"]
        cat["totalCasesCurrent"] += metrics["totalCases"]["value"]
        cat["totalCasesPrevious"] += metrics["totalCases"]["previousValue"]

        if metrics["avgCaseLife"]["value"] > 0:
            cat["avgResolutionSum"] += metrics["avgCaseLife"]["value"]
            cat["avgResolutionCount"] += 1

        if metrics["resolutionRate"]["value"] > 0:
            cat["resolutionRateSum"] += metrics["resolutionRate"]["value"]
            cat["resolutionRateCount"] += 1

        cat["products"].append(product)

    # Calculate averages and format response
    category_metrics = []
    for category_name, cat in category_map.items():
        avg_resolution = (cat["avgResolutionSum"] / cat["avgResolutionCount"]) if cat["avgResolutionCount"] > 0 else 0
        avg_resolution_rate = (cat["resolutionRateSum"] / cat["resolutionRateCount"]) if cat["resolutionRateCount"] > 0 else 0

        # Calculate trend
        change = cat["totalCasesCurrent"] - cat["totalCasesPrevious"]
        change_pct = (change / cat["totalCasesPrevious"] * 100) if cat["totalCasesPrevious"] > 0 else 0
        change_type = "increase" if change > 0 else ("decrease" if change < 0 else "neutral")

        category_metrics.append(
            {
                "categoryName": category_name,
                "totalCases": cat["totalCases"],
                "casesChange": change,
                "casesChangePercentage": round(change_pct, 1),
                "changeType": change_type,
                "avgResolution": round(avg_resolution, 1),
                "resolutionRate": round(avg_resolution_rate, 1),
                "productCount": len(cat["products"]),
            }
        )

    # Sort by total cases descending
    category_metrics.sort(key=lambda x: x["totalCases"], reverse=True)

    return category_metrics


def get_subcategory_metrics(
    period: str,
    category: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get subcategory-level metrics for a specific category.

    Args:
        period: Time period ('week', 'month', 'custom')
        category: Parent category name
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)

    Returns:
        List of subcategory metrics dictionaries
    """
    session = snowflake_service._get_session()
    tables = get_active_configuration()

    # Map custom period to week (default behavior)
    display_period = "week" if period == "custom" else period

    # Query products table filtered by category
    query = f"""
    SELECT
        PRODUCT_SUBCATEGORY,
        PRODUCT_CATEGORY,
        METRICS
    FROM {tables["products"]}
    WHERE PRODUCT_CATEGORY = '{category.replace("'", "''")}'
    """

    results = session.sql(query).collect()

    # Group by subcategory and aggregate
    subcategory_map: dict[str, dict[str, Any]] = {}

    for row in results:
        subcategory = row[0]
        if not subcategory:
            continue

        metrics_json = json.loads(str(row[2])) if isinstance(row[2], str) else row[2]
        period_metrics = metrics_json.get(display_period, {})
        current_metrics = period_metrics.get("current", {})
        previous_metrics = period_metrics.get("previous", {})

        if subcategory not in subcategory_map:
            subcategory_map[subcategory] = {
                "subcategoryName": subcategory,
                "categoryName": category,
                "totalCasesCurrent": 0,
                "totalCasesPrevious": 0,
                "avgResolutionSum": 0.0,
                "avgResolutionCount": 0,
                "resolutionRateSum": 0.0,
                "resolutionRateCount": 0,
            }

        subcat = subcategory_map[subcategory]

        # Aggregate
        total_cases_current = current_metrics.get("totalCases", {}).get("value", 0)
        total_cases_previous = previous_metrics.get("totalCases", {}).get("value", 0)
        avg_case_life = current_metrics.get("avgCaseLife", {}).get("value", 0)
        resolution_rate = current_metrics.get("resolutionRate", {}).get("value", 0)

        subcat["totalCasesCurrent"] += total_cases_current
        subcat["totalCasesPrevious"] += total_cases_previous

        if avg_case_life > 0:
            subcat["avgResolutionSum"] += avg_case_life
            subcat["avgResolutionCount"] += 1

        if resolution_rate > 0:
            subcat["resolutionRateSum"] += resolution_rate
            subcat["resolutionRateCount"] += 1

    # Calculate averages and format response
    subcategory_metrics = []
    for subcategory_name, subcat in subcategory_map.items():
        avg_resolution = (subcat["avgResolutionSum"] / subcat["avgResolutionCount"]) if subcat["avgResolutionCount"] > 0 else 0
        avg_resolution_rate = (subcat["resolutionRateSum"] / subcat["resolutionRateCount"]) if subcat["resolutionRateCount"] > 0 else 0

        # Calculate trend
        change = subcat["totalCasesCurrent"] - subcat["totalCasesPrevious"]
        change_pct = (change / subcat["totalCasesPrevious"] * 100) if subcat["totalCasesPrevious"] > 0 else 0
        change_type = "increase" if change > 0 else ("decrease" if change < 0 else "neutral")

        subcategory_metrics.append(
            {
                "subcategoryName": subcategory_name,
                "categoryName": category,
                "totalCases": subcat["totalCasesCurrent"],
                "casesChange": change,
                "casesChangePercentage": round(change_pct, 1),
                "changeType": change_type,
                "avgResolution": round(avg_resolution, 1),
                "resolutionRate": round(avg_resolution_rate, 1),
            }
        )

    # Sort by total cases descending
    subcategory_metrics.sort(key=lambda x: x["totalCases"], reverse=True)

    return subcategory_metrics


def get_product_benchmarks(
    period: str,
    category: str | None = None,
    subcategory: str | None = None,
    product_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Get benchmarking data showing top/bottom performers and averages.

    Args:
        period: Time period ('week', 'month', 'custom')
        category: Optional category filter
        subcategory: Optional subcategory filter
        product_id: Optional specific product to benchmark
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)

    Returns:
        Dictionary with scope, average, top/bottom performers, and optional yourProduct
    """
    # Get all products
    product_metrics = get_product_metrics(period, start_date, end_date, None, None, None if not category else [category])

    # Filter by subcategory if provided
    if subcategory:
        product_metrics = [p for p in product_metrics if p.get("productSubcategory") == subcategory]

    if len(product_metrics) == 0:
        return {
            "scope": subcategory or category or "All Products",
            "average": {"cases": 0, "time": 0, "rate": 0},
            "topPerformer": None,
            "bottomPerformer": None,
            "yourProduct": None,
        }

    # Calculate averages
    total_cases_sum = sum(p["metrics"]["totalCases"]["value"] for p in product_metrics)
    avg_cases = total_cases_sum / len(product_metrics)

    avg_time_sum = sum(p["metrics"]["avgCaseLife"]["value"] for p in product_metrics if p["metrics"]["avgCaseLife"]["value"] > 0)
    avg_time_count = len([p for p in product_metrics if p["metrics"]["avgCaseLife"]["value"] > 0])
    avg_time = avg_time_sum / avg_time_count if avg_time_count > 0 else 0

    avg_rate_sum = sum(p["metrics"]["resolutionRate"]["value"] for p in product_metrics if p["metrics"]["resolutionRate"]["value"] > 0)
    avg_rate_count = len([p for p in product_metrics if p["metrics"]["resolutionRate"]["value"] > 0])
    avg_rate = avg_rate_sum / avg_rate_count if avg_rate_count > 0 else 0

    # Find top/bottom performers by case volume
    sorted_by_cases = sorted(product_metrics, key=lambda p: p["metrics"]["totalCases"]["value"], reverse=True)
    top_performer = {
        "id": sorted_by_cases[0]["productId"],
        "name": sorted_by_cases[0]["productName"],
        "cases": sorted_by_cases[0]["metrics"]["totalCases"]["value"],
        "time": sorted_by_cases[0]["metrics"]["avgCaseLife"]["value"],
        "rate": sorted_by_cases[0]["metrics"]["resolutionRate"]["value"],
    }
    bottom_performer = {
        "id": sorted_by_cases[-1]["productId"],
        "name": sorted_by_cases[-1]["productName"],
        "cases": sorted_by_cases[-1]["metrics"]["totalCases"]["value"],
        "time": sorted_by_cases[-1]["metrics"]["avgCaseLife"]["value"],
        "rate": sorted_by_cases[-1]["metrics"]["resolutionRate"]["value"],
    }

    # Find best performer by resolution time (fastest = lowest time)
    sorted_by_time = sorted([p for p in product_metrics if p["metrics"]["avgCaseLife"]["value"] > 0], key=lambda p: p["metrics"]["avgCaseLife"]["value"])
    best_time_performer = None
    if len(sorted_by_time) > 0:
        best_time_performer = {
            "id": sorted_by_time[0]["productId"],
            "name": sorted_by_time[0]["productName"],
            "time": sorted_by_time[0]["metrics"]["avgCaseLife"]["value"],
        }

    # Find best performer by resolution rate (highest rate)
    sorted_by_rate = sorted([p for p in product_metrics if p["metrics"]["resolutionRate"]["value"] > 0], key=lambda p: p["metrics"]["resolutionRate"]["value"], reverse=True)
    best_rate_performer = None
    if len(sorted_by_rate) > 0:
        best_rate_performer = {
            "id": sorted_by_rate[0]["productId"],
            "name": sorted_by_rate[0]["productName"],
            "rate": sorted_by_rate[0]["metrics"]["resolutionRate"]["value"],
        }

    # If product_id provided, find that specific product
    your_product = None
    if product_id:
        for p in product_metrics:
            if p["productId"] == product_id:
                your_product = {
                    "id": p["productId"],
                    "name": p["productName"],
                    "cases": p["metrics"]["totalCases"]["value"],
                    "time": p["metrics"]["avgCaseLife"]["value"],
                    "rate": p["metrics"]["resolutionRate"]["value"],
                }
                break

    return {
        "scope": subcategory or category or "All Products",
        "average": {
            "cases": round(avg_cases, 1),
            "time": round(avg_time, 1),
            "rate": round(avg_rate, 1),
        },
        "topPerformer": top_performer,
        "bottomPerformer": bottom_performer,
        "bestTimePerformer": best_time_performer,
        "bestRatePerformer": best_rate_performer,
        "yourProduct": your_product,
    }


def search_products(
    query: str,
    category: str | None = None,
    subcategory: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search products by name with optional category/subcategory filters.

    Args:
        query: Search query string
        category: Optional category filter
        subcategory: Optional subcategory filter

    Returns:
        List of matching products with id and name
    """
    session = snowflake_service._get_session()
    tables = get_active_configuration()

    # Build filter conditions
    escaped_query = query.replace("'", "''")
    filter_conditions = [f"UPPER(PRODUCT_NAME) LIKE UPPER('%{escaped_query}%')"]

    if category:
        escaped_category = category.replace("'", "''")
        filter_conditions.append(f"PRODUCT_CATEGORY = '{escaped_category}'")

    if subcategory:
        escaped_subcategory = subcategory.replace("'", "''")
        filter_conditions.append(f"GENERATED_PRODUCT_SUBCATEGORY = '{escaped_subcategory}'")

    where_clause = " AND ".join(filter_conditions)

    search_query = f"""
    SELECT
        PRODUCT_ID,
        PRODUCT_NAME,
        PRODUCT_CATEGORY,
        GENERATED_PRODUCT_SUBCATEGORY
    FROM {tables["products"]}
    WHERE {where_clause}
    ORDER BY PRODUCT_NAME
    LIMIT 50
    """

    results = session.sql(search_query).collect()

    return [
        {
            "productId": row[0],
            "productName": row[1],
            "productCategory": row[2],
            "productSubcategory": row[3],
        }
        for row in results
    ]
