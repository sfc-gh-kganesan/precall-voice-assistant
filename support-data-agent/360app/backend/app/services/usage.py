"""
Usage analytics service for querying Cortex Search usage metrics from Snowflake.
"""

from typing import Any

from . import snowflake as snowflake_service


def get_credits_timeline(
    date_range: str | None = None,
    certified_organization_type: str = "Customer",
    certified_deployment: str = "All",
    certified_salesforce_account_id: str | None = None,
    certified_salesforce_account_name: str | None = None,
    include_coda: bool = False,
) -> list[dict[str, Any]]:
    """
    Get credits consumption timeline with rolling 7-day average.

    Returns list of {ds, credits, rolling_avg_7d}
    """
    session = snowflake_service._get_session()

    # Default to last 30 days if no date range specified
    date_filter = "ds >= DATEADD(day, -30, CURRENT_DATE())" if not date_range else f"ds = '{date_range}'"

    account_filters = []
    if certified_organization_type:
        account_filters.append(f"snowflake_account_type = '{certified_organization_type}'")
    if certified_deployment and certified_deployment != "All":
        account_filters.append(f"snowflake_deployment = '{certified_deployment}'")
    if certified_salesforce_account_id:
        account_filters.append(f"salesforce_account_id = '{certified_salesforce_account_id}'")
    if certified_salesforce_account_name:
        account_filters.append(f"salesforce_account_name = '{certified_salesforce_account_name}'")

    account_filter_clause = " AND ".join(account_filters) if account_filters else "1=1"

    coda_filter = ""
    if not include_coda:
        coda_filter = "AND salesforce_account_id NOT IN ('001VI000008yBaJYAU', '0010Z00001wlN8VQAU')"

    query = f"""
    WITH time_series AS (
        SELECT ds,
               SUM(j.credits) AS credits
        FROM snowscience.llm.cortex_search_accounts_credits j
        JOIN snowscience.dimensions.dim_accounts_history a
            ON j.deployment = a.snowflake_deployment
            AND j.account_id = a.snowflake_account_id
            AND j.ds::date - 1 = a.general_date::date
        WHERE {date_filter}
            AND ds >= '2024-03-25'
            AND {account_filter_clause}
            {coda_filter}
        GROUP BY ALL
    )
    SELECT
        ds,
        ROUND(credits, 2) AS credits,
        ROUND(AVG(credits) OVER (ORDER BY ds ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS rolling_avg_7d
    FROM time_series
    ORDER BY ds DESC
    """

    results = session.sql(query).collect()

    return [
        {
            "ds": str(row[0]),
            "credits": float(row[1]) if row[1] else 0.0,
            "rolling_avg_7d": float(row[2]) if row[2] else 0.0,
        }
        for row in results
    ]


def get_top_accounts_by_serving_rows(
    certified_organization_type: str = "Customer",
    certified_deployment: str = "All",
    certified_salesforce_account_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get top accounts ranked by total active serving rows.

    Returns list of account details with serving metrics.
    """
    session = snowflake_service._get_session()

    account_filters = []
    if certified_organization_type:
        account_filters.append(f"snowflake_account_type = '{certified_organization_type}'")
    if certified_deployment and certified_deployment != "All":
        account_filters.append(f"snowflake_deployment = '{certified_deployment}'")
    if certified_salesforce_account_name:
        account_filters.append(f"snowflake_account_name = '{certified_salesforce_account_name}'")

    account_filter_clause = " AND ".join(account_filters) if account_filters else "1=1"

    query = f"""
    WITH active_services AS (
        SELECT c.ds,
               c.created_on,
               a.salesforce_account_name,
               a.salesforce_account_id,
               c.cortexnumrowsread,
               c.deployment,
               CASE
                    WHEN c.dpo['CortexSearchServiceDPO:primary']['servingSuspendedOn']::number > 0 THEN 'suspended'
                    ELSE 'active'
               END AS serving_status,
               snowflake_account_type,
               snowflake_account_name,
               a.industry,
               a.sub_industry,
               a.segment,
               CONCAT(c.deployment, c.account_id, c.id) AS uuid
        FROM snowscience.llm.cortex_search_daily_active_services c
        JOIN snowscience.dimensions.dim_accounts_history a
            ON c.deployment = a.snowflake_deployment
            AND c.account_id = a.snowflake_account_id
            AND c.ds::date - 1 = a.general_date::date
        WHERE c.ds = (SELECT MAX(ds) FROM snowscience.llm.cortex_search_daily_active_services)
            AND {account_filter_clause}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY c.id, c.deployment ORDER BY c.ds DESC) = 1
    )
    SELECT
        s.ds,
        s.salesforce_account_name,
        s.salesforce_account_id,
        SUM(cortexnumrowsread) AS total_indexed_rows,
        SUM(CASE WHEN serving_status = 'active' THEN cortexnumrowsread ELSE 0 END) AS total_active_serving_rows,
        COUNT(DISTINCT uuid) AS num_services,
        s.snowflake_account_type,
        MIN(created_on) AS acct_first_svc_creation_date,
        a.sales_engineer_email,
        ARRAY_AGG(DISTINCT OBJECT_CONSTRUCT('deployment', deployment, 'account', snowflake_account_name)) AS accounts
    FROM active_services s
    LEFT JOIN SALES.ETM.ACCOUNT_TO_TERRITORY_ASSOCIATION a
        ON s.salesforce_account_id = a.id
        AND a.ds::date = CURRENT_DATE() - 1
    GROUP BY s.ds, s.salesforce_account_name, s.salesforce_account_id, s.snowflake_account_type, a.sales_engineer_email
    ORDER BY total_active_serving_rows DESC
    """

    results = session.sql(query).collect()

    return [
        {
            "ds": str(row[0]),
            "salesforce_account_name": str(row[1]),
            "salesforce_account_id": str(row[2]),
            "total_indexed_rows": int(row[3]) if row[3] else 0,
            "total_active_serving_rows": int(row[4]) if row[4] else 0,
            "num_services": int(row[5]) if row[5] else 0,
            "snowflake_account_type": str(row[6]) if row[6] else "",
            "acct_first_svc_creation_date": str(row[7]) if row[7] else "",
            "sales_engineer_email": str(row[8]) if row[8] else None,
            "accounts": row[9] if row[9] else [],
        }
        for row in results
    ]


def get_biggest_movers_7d(
    certified_organization_type: str = "Customer",
    certified_deployment: str = "All",
    certified_salesforce_account_id: str | None = None,
    certified_salesforce_account_name: str | None = None,
    include_coda: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """
    Get top 5 gainers and top 5 decliners by 7-day credit change.

    Returns dict with 'gainers' and 'decliners' lists.
    """
    session = snowflake_service._get_session()

    account_filters = []
    if certified_organization_type:
        account_filters.append(f"snowflake_account_type = '{certified_organization_type}'")
    if certified_deployment and certified_deployment != "All":
        account_filters.append(f"snowflake_deployment = '{certified_deployment}'")
    if certified_salesforce_account_id:
        account_filters.append(f"salesforce_account_id = '{certified_salesforce_account_id}'")
    if certified_salesforce_account_name:
        account_filters.append(f"salesforce_account_name = '{certified_salesforce_account_name}'")

    account_filter_clause = " AND ".join(account_filters) if account_filters else "1=1"

    coda_filter = ""
    if not include_coda:
        coda_filter = "AND salesforce_account_id NOT IN ('001VI000008yBaJYAU', '0010Z00001wlN8VQAU')"

    query = f"""
    WITH l14_daily AS (
        SELECT
            ds,
            a.salesforce_account_name,
            a.salesforce_account_id,
            ROUND(SUM(j.credits), 2) AS total_credits,
            ROUND(SUM(CASE WHEN j.segment = 'EMBED_TEXT Token Credits' THEN j.credits ELSE 0 END), 2) AS embed_text_token_credits,
            ROUND(SUM(CASE WHEN j.segment = 'DT Refresh Credits' THEN j.credits ELSE 0 END), 2) AS dt_refresh_credits,
            ROUND(SUM(CASE WHEN j.segment = 'Serving Credits' THEN j.credits ELSE 0 END), 2) AS serving_credits
        FROM snowscience.llm.cortex_search_accounts_credits j
        JOIN snowscience.dimensions.dim_accounts_history a
            ON j.deployment = a.snowflake_deployment
            AND j.account_id = a.snowflake_account_id
            AND j.ds::date - 1 = a.general_date::date
        WHERE ds >= CURRENT_DATE() - 14
            AND {account_filter_clause}
            {coda_filter}
        GROUP BY ALL
    ),
    l7_minus_7 AS (
        SELECT
            salesforce_account_name,
            salesforce_account_id,
            SUM(total_credits) AS l7_minus_7_total_credits
        FROM l14_daily
        WHERE ds <= CURRENT_DATE() - 8
        GROUP BY ALL
    ),
    l7 AS (
        SELECT
            salesforce_account_name,
            salesforce_account_id,
            SUM(total_credits) AS l7_total_credits
        FROM l14_daily
        WHERE ds > CURRENT_DATE() - 8
        GROUP BY ALL
    ),
    winner AS (
        SELECT
            l7.salesforce_account_name,
            COALESCE(l7_total_credits, 0) AS l7_total_credits,
            l7_total_credits - COALESCE(l7_minus_7_total_credits, 0) AS delta,
            delta / NULLIF(l7_minus_7_total_credits, 0) AS pct_change,
            accts.sales_engineer_email,
            l7.salesforce_account_id,
            acct_rev.is_cap1,
            acct_rev.agreement_type
        FROM l7
        LEFT JOIN l7_minus_7
            ON l7.salesforce_account_id = l7_minus_7.salesforce_account_id
        LEFT JOIN SALES.ETM.ACCOUNT_TO_TERRITORY_ASSOCIATION accts
            ON l7.salesforce_account_id = accts.id
        LEFT JOIN (
            SELECT salesforce_account_id, MAX(is_cap1) AS is_cap1, MAX(agreement_type) AS agreement_type
            FROM finance.customer.snowflake_account_revenue
            WHERE general_date::date = CURRENT_DATE() - 1
            GROUP BY ALL
        ) acct_rev
            ON l7.salesforce_account_id = acct_rev.salesforce_account_id
        WHERE accts.ds::date = CURRENT_DATE() - 1
        ORDER BY delta DESC
        LIMIT 5
    ),
    loser AS (
        SELECT
            l7_minus_7.salesforce_account_name,
            COALESCE(l7_total_credits, 0) AS l7_total_credits,
            COALESCE(l7_total_credits, 0) - l7_minus_7_total_credits AS delta,
            delta / NULLIF(l7_minus_7_total_credits, 0) AS pct_change,
            accts.sales_engineer_email,
            l7_minus_7.salesforce_account_id,
            acct_rev.is_cap1,
            acct_rev.agreement_type
        FROM l7_minus_7
        LEFT JOIN l7
            ON l7.salesforce_account_id = l7_minus_7.salesforce_account_id
        LEFT JOIN SALES.ETM.ACCOUNT_TO_TERRITORY_ASSOCIATION accts
            ON l7_minus_7.salesforce_account_id = accts.id
        LEFT JOIN (
            SELECT salesforce_account_id, MAX(is_cap1) AS is_cap1, MAX(agreement_type) AS agreement_type
            FROM finance.customer.snowflake_account_revenue
            WHERE general_date::date = CURRENT_DATE() - 1
            GROUP BY ALL
        ) acct_rev
            ON l7_minus_7.salesforce_account_id = acct_rev.salesforce_account_id
        WHERE accts.ds::date = CURRENT_DATE() - 1
        ORDER BY delta ASC
        LIMIT 5
    )
    SELECT *, 'gainer' AS type FROM winner
    UNION ALL
    SELECT *, 'decliner' AS type FROM loser
    """

    results = session.sql(query).collect()

    gainers = []
    decliners = []

    for row in results:
        mover = {
            "salesforce_account_name": str(row[0]),
            "salesforce_account_id": str(row[5]),
            "l7_total_credits": float(row[1]) if row[1] else 0.0,
            "delta": float(row[2]) if row[2] else 0.0,
            "pct_change": float(row[3]) if row[3] is not None else None,
            "sales_engineer_email": str(row[4]) if row[4] else None,
            "is_cap1": bool(row[6]) if row[6] is not None else None,
            "agreement_type": str(row[7]) if row[7] else None,
        }

        if row[8] == "gainer":
            gainers.append(mover)
        else:
            decliners.append(mover)

    return {
        "gainers": gainers,
        "decliners": decliners,
    }


def get_usage_metrics_summary() -> dict[str, Any]:
    """
    Get high-level usage metrics summary (for KPI cards).

    Returns total credits, active accounts, and 7d change percentages.
    """
    # Get last 14 days of credits to calculate trends
    timeline = get_credits_timeline(date_range=None)

    if not timeline:
        return {
            "total_credits": 0.0,
            "total_credits_change": 0.0,
            "total_credits_change_pct": 0.0,
            "active_accounts": 0,
            "active_accounts_change": 0,
            "seven_day_change_pct": 0.0,
        }

    # Get last 7 days and previous 7 days
    last_7_days = timeline[:7] if len(timeline) >= 7 else timeline
    prev_7_days = timeline[7:14] if len(timeline) >= 14 else []

    last_7_total = sum(point["credits"] for point in last_7_days)
    prev_7_total = sum(point["credits"] for point in prev_7_days) if prev_7_days else last_7_total

    credits_change = last_7_total - prev_7_total
    credits_change_pct = (credits_change / prev_7_total * 100) if prev_7_total > 0 else 0.0

    # Get account counts
    accounts = get_top_accounts_by_serving_rows()
    active_accounts = len(accounts)

    return {
        "total_credits": last_7_total,
        "total_credits_change": credits_change,
        "total_credits_change_pct": round(credits_change_pct, 1),
        "active_accounts": active_accounts,
        "active_accounts_change": 0,  # TODO: Calculate from historical data
        "seven_day_change_pct": round(credits_change_pct, 1),
    }


def get_case_counts_by_account(product_name: str, days: int = 30) -> dict[str, int]:
    """
    Get case counts by account for a specific product.

    Args:
        product_name: Product name to filter cases by
        days: Number of days to look back (default 30)

    Returns:
        Dictionary mapping account_name -> case_count
    """
    from . import snowflake as snowflake_service
    from .configuration import get_active_configuration

    session = snowflake_service._get_session()
    tables = get_active_configuration()

    query = f"""
    SELECT
        ACCOUNT_NAME,
        COUNT(*) as case_count
    FROM {tables["output"]}
    WHERE GENERATED_PRODUCT = '{product_name}'
        AND CREATED_AT >= DATEADD(day, -{days}, CURRENT_DATE())
    GROUP BY ACCOUNT_NAME
    """

    results = session.sql(query).collect()

    return {str(row[0]): int(row[1]) for row in results}
