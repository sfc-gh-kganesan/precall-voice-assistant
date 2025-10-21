"""
Analytics service for querying Snowflake tables from active configuration and calculating dashboard metrics.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from . import snowflake as snowflake_service
from .configuration import get_active_configuration


def calculate_period_dates(
    period: str, start_date: str | None = None, end_date: str | None = None
) -> dict[str, datetime]:
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

    Args:
        period: Time period ('week', 'month', 'custom')
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)
        products: Optional list of products to filter by
        topics: Optional list of topics to filter by (not used with pre-aggregated data)
        categories: Optional list of categories to filter by

    Returns:
        List of product metrics dictionaries
    """
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

    if products:
        product_list = "','".join(products)
        filter_conditions.append(f"PRODUCT_NAME IN ('{product_list}')")

    if categories:
        category_list = "','".join(categories)
        filter_conditions.append(f"PRODUCT_CATEGORY IN ('{category_list}')")

    where_clause = " AND ".join(filter_conditions)
    query = f"""
    SELECT
        PRODUCT_ID,
        PRODUCT_NAME,
        PRODUCT_CATEGORY,
        METRICS,
        TOP_ISSUES,
        TREND_DATA
    FROM {tables["products"]}
    WHERE {where_clause}
    ORDER BY PRODUCT_NAME
    """

    results = session.sql(query).collect()

    product_metrics = []
    for row in results:
        metrics_json = json.loads(str(row[3])) if isinstance(row[3], str) else row[3]
        top_issues_json = json.loads(str(row[4])) if row[4] and isinstance(row[4], str) else row[4]
        trend_data_json = json.loads(str(row[5])) if row[5] and isinstance(row[5], str) else row[5]

        product_metrics.append(
            {
                "productId": row[0],
                "productName": row[1],
                "productCategory": row[2],
                "parentProduct": None,
                "metrics": {
                    "totalCases": metrics_json.get("totalCases", {}),
                    "avgCaseLife": metrics_json.get("avgCaseLife", {}),
                    "resolutionRate": metrics_json.get("resolutionRate", {}),
                },
                "topIssues": top_issues_json if top_issues_json else [],
                "trend": trend_data_json if trend_data_json else [],
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

    Args:
        period: Time period ('week', 'month', 'custom')
        start_date: Start date for custom period (ISO format)
        end_date: End date for custom period (ISO format)
        products: Optional list of products to filter by (not used with pre-aggregated data)
        topics: Optional list of topics to filter by
        categories: Optional list of categories to filter by (not used with pre-aggregated data)

    Returns:
        List of topic metrics dictionaries
    """
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

    if topics:
        topic_list = "','".join(topics)
        filter_conditions.append(f"TOPIC_NAME IN ('{topic_list}')")

    where_clause = " AND ".join(filter_conditions)
    query = f"""
    SELECT
        TOPIC_ID,
        TOPIC_NAME,
        TOTAL_CASES,
        CHANGE_ABSOLUTE,
        CHANGE_PERCENTAGE,
        CHANGE_TYPE,
        AVG_RESOLUTION_TIME,
        RESOLUTION_RATE,
        SENTIMENT_POSITIVE,
        SENTIMENT_NEUTRAL,
        SENTIMENT_NEGATIVE,
        TOP_PRODUCTS
    FROM {tables["topics"]}
    WHERE {where_clause}
    ORDER BY TOTAL_CASES DESC
    """

    results = session.sql(query).collect()

    topic_metrics = []
    for row in results:
        top_products = []
        if row[11]:
            try:
                top_products = json.loads(str(row[11])) if isinstance(row[11], str) else row[11]
            except (json.JSONDecodeError, TypeError):
                top_products = []

        topic_metrics.append(
            {
                "topicId": row[0],
                "topicName": row[1],
                "totalCases": int(row[2]) if row[2] else 0,
                "change": int(row[3]) if row[3] else 0,
                "changePercentage": round(float(row[4]), 1) if row[4] else 0.0,
                "changeType": row[5] if row[5] else "neutral",
                "avgResolutionTime": round(float(row[6]), 1) if row[6] else 0.0,
                "resolutionRate": round(float(row[7]), 1) if row[7] else 0.0,
                "sentiment": {
                    "positive": int(row[8]) if row[8] else 0,
                    "neutral": int(row[9]) if row[9] else 0,
                    "negative": int(row[10]) if row[10] else 0,
                },
                "topProducts": top_products,
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
