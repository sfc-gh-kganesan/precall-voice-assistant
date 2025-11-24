"""
Native MCP Server for DDA Service

Implements all DDA endpoints as native FastMCP tools.
This provides direct MCP tool implementations instead of auto-converting FastAPI routes.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from app.services.account_service import AccountService
from app.services.case_service import CaseService
from app.services.jira_service import JiraService
from app.services.query_service import QueryService
from app.services.tsw_service import TswService
from app.services.warehouse_service import WarehouseService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP(name="DDA Diagnostic Service (Native)")


# ============================================================================
# CASES ENDPOINTS (3 tools)
# ============================================================================


@mcp.tool()
def get_case(case_number: str) -> Dict[str, Any]:
    """
    Get case metadata from Salesforce.

    Returns comprehensive metadata for a specific Salesforce case including
    status, priority, dates, owner, and account information.

    Args:
        case_number: Salesforce case number (e.g., "01087579")

    Returns:
        Dict containing case metadata
    """
    try:
        case_service = CaseService()
        result = case_service.get_case_metadata(case_number)

        if result is None:
            return {"error": f"Case not found: {case_number}"}

        return result
    except Exception as e:
        logger.error(f"Error fetching case {case_number}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_case_queries(case_number: str) -> Dict[str, Any]:
    """
    Get all queries associated with a case.

    Returns list of queries linked to this case through various mappings
    (DDA, adhoc relations, query metadata).

    Args:
        case_number: Salesforce case number

    Returns:
        Dict with query count and list of queries with metadata
    """
    try:
        case_service = CaseService()
        queries = case_service.get_case_queries(case_number)
        count = case_service.get_case_query_count(case_number)

        return {"case_number": case_number, "query_count": count, "queries": queries}
    except Exception as e:
        logger.error(f"Error fetching queries for case {case_number}: {e}")
        return {"error": str(e)}


@mcp.tool()
def search_cases(
    status: Optional[str] = None,
    is_closed: Optional[bool] = None,
    functional_area: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Search cases by various criteria.

    Args:
        status: Case status filter (Open, Closed, etc.)
        is_closed: Boolean closed status filter
        functional_area: Functional area filter (Performance, Security, etc.)
        start_date: Filter cases created after this date (ISO format)
        end_date: Filter cases created before this date (ISO format)
        limit: Maximum number of results (1-1000, default 100)

    Returns:
        Dict with count and list of matching cases
    """
    try:
        case_service = CaseService()

        # Convert string dates to datetime if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        results = case_service.search_cases(
            status=status,
            is_closed=is_closed,
            functional_area=functional_area,
            start_date=start_dt,
            end_date=end_dt,
            limit=min(limit, 1000),
        )

        return {"count": len(results), "cases": results}
    except Exception as e:
        logger.error(f"Error searching cases: {e}")
        return {"error": str(e)}


# ============================================================================
# QUERIES ENDPOINTS (12 tools)
# ============================================================================


@mcp.tool()
def get_query_metadata(query_id: str) -> Dict[str, Any]:
    """
    Get comprehensive query metadata including all duration breakdowns.

    Returns 18+ duration metrics, query statistics, error information,
    and execution details.

    Args:
        query_id: Snowflake query ID (UUID format)

    Returns:
        Dict with comprehensive query metadata
    """
    try:
        service = QueryService()
        result = service.get_query_metadata(query_id)

        if not result:
            return {"error": f"Query with ID '{query_id}' not found"}

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching query metadata for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_historical_runs(query_id: str, limit: int = 1000) -> Dict[str, Any]:
    """
    Get historical runs of queries with the same SQL hash.

    Returns historical query executions that share the same SQL fingerprint,
    useful for performance comparison analysis.

    Args:
        query_id: Snowflake query ID
        limit: Maximum number of historical runs to return (max 10000)

    Returns:
        Dict with list of historical query runs
    """
    try:
        service = QueryService()
        result = service.get_historical_runs(query_id, min(limit, 10000))

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching historical runs for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_concurrent_queries(
    query_id: str,
    cluster_number: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get queries that ran concurrently in the same warehouse.

    Returns queries that were executing at the same time in the same warehouse,
    useful for analyzing contention and performance impact.

    Args:
        query_id: Snowflake query ID
        cluster_number: Optional filter by cluster number

    Returns:
        Dict with list of concurrent queries
    """
    try:
        service = QueryService()
        result = service.get_concurrent_queries(query_id, cluster_number)

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching concurrent queries for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_gs_logs(query_id: str, limit: int = 1000) -> Dict[str, Any]:
    """
    Get Global Services (GS) logs for a query.

    Returns GS-layer logs which include metadata service operations,
    authentication, and query planning activities.

    Args:
        query_id: Snowflake query ID
        limit: Maximum number of log entries (max 10000)

    Returns:
        Dict with GS logs
    """
    try:
        service = QueryService()
        result = service.get_gs_logs(query_id, min(limit, 10000))

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching GS logs for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_xp_logs(query_id: str, limit: int = 1000) -> Dict[str, Any]:
    """
    Get Execution Platform (XP) logs for a query.

    Returns XP-layer logs which include query execution details,
    virtual warehouse operations, and compute resource usage.

    Args:
        query_id: Snowflake query ID
        limit: Maximum number of log entries (max 10000)

    Returns:
        Dict with XP logs
    """
    try:
        service = QueryService()
        result = service.get_xp_logs(query_id, min(limit, 10000))

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching XP logs for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_query_parameters(query_id: str) -> Dict[str, Any]:
    """
    Get non-default parameters for a query.

    Returns session and account parameters that differ from default values,
    which can significantly impact query behavior and performance.

    Args:
        query_id: Snowflake query ID

    Returns:
        Dict with non-default parameters
    """
    try:
        service = QueryService()
        result = service.get_parameters(query_id)

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching parameters for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_query_incidents(query_id: str, limit: int = 5) -> Dict[str, Any]:
    """
    Get incidents from Crash Manager for a query.

    Returns incidents and crashes related to this query execution,
    useful for identifying systemic issues or bugs.

    Args:
        query_id: Snowflake query ID
        limit: Maximum number of incidents (max 20)

    Returns:
        Dict with incidents
    """
    try:
        service = QueryService()
        result = service.get_incidents(query_id, min(limit, 20))

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching incidents for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_parent_child_tree(query_id: str) -> Dict[str, Any]:
    """
    Get parent-child query execution tree.

    Returns the hierarchical relationship between parent and child queries,
    useful for analyzing stored procedure and complex query execution flows.

    Args:
        query_id: Snowflake query ID

    Returns:
        Dict with parent-child tree structure
    """
    try:
        service = QueryService()
        result = service.get_parent_child_tree(query_id)

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching parent-child tree for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_processing_status(query_id: str) -> Dict[str, Any]:
    """
    Get DDA pipeline processing status (0-100%).

    Returns the current processing status of the query through the
    DDA data pipeline, indicating data availability.

    Args:
        query_id: Snowflake query ID

    Returns:
        Dict with processing status percentage
    """
    try:
        service = QueryService()
        result = service.get_processing_status(query_id)

        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching processing status for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def trigger_adhoc_process(query_id: str, case_number: str) -> Dict[str, Any]:
    """
    Trigger adhoc DDA pipeline processing.

    Initiates on-demand processing of a query through the DDA pipeline,
    useful for urgent case analysis or when automatic processing hasn't completed.

    Args:
        query_id: Snowflake query ID to process
        case_number: Associated Salesforce case number

    Returns:
        Dict with processing request status
    """
    try:
        # For MVP, use placeholder user email
        user_email = "api_user@snowflake.com"

        service = QueryService()
        result = service.trigger_adhoc_process(query_id, case_number, user_email)

        return {"data": result}
    except Exception as e:
        logger.error(f"Error triggering adhoc process for {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def compare_queries(query_id_1: str, query_id_2: str) -> Dict[str, Any]:
    """
    Compare two queries (metadata, parameters, performance).

    Returns a detailed comparison of two query executions, highlighting
    differences in performance, resource usage, and configuration.

    Args:
        query_id_1: First Snowflake query ID
        query_id_2: Second Snowflake query ID

    Returns:
        Dict with comparison results
    """
    try:
        service = QueryService()
        result = service.compare_queries(query_id_1, query_id_2)

        if "error" in result:
            return result

        return {"data": result}
    except Exception as e:
        logger.error(f"Error comparing queries {query_id_1} and {query_id_2}: {e}")
        return {"error": str(e)}


# ============================================================================
# TSW DIAGNOSTICS ENDPOINTS (7 tools)
# ============================================================================


@mcp.tool()
def analyze_udf(query_id: str) -> Dict[str, Any]:
    """
    Analyze UDF (User-Defined Function) usage for a query.

    Returns query metadata, UDF analysis results from stored procedure,
    and tables accessed by the query.

    Args:
        query_id: Snowflake query ID

    Returns:
        Dict with UDF analysis results
    """
    try:
        service = TswService()
        result = service.analyze_udf(query_id)

        if not result:
            return {"error": f"No UDF data found for query: {query_id}"}

        return result
    except Exception as e:
        logger.error(f"Error analyzing UDF for query {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def analyze_compilation(case_number: str) -> Dict[str, Any]:
    """
    Analyze query compilation issues for a case.

    Returns metadata for all queries in the case, queries with high compilation time,
    and pre-computed package data if available.

    Args:
        case_number: Salesforce case number

    Returns:
        Dict with compilation analysis results
    """
    try:
        service = TswService()
        result = service.analyze_compilation(case_number)

        if not result:
            return {"error": f"No compilation data found for case: {case_number}"}

        return result
    except Exception as e:
        logger.error(f"Error analyzing compilation for case {case_number}: {e}")
        return {"error": str(e)}


@mcp.tool()
def analyze_iceberg(
    query_id: str,
    case_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze Iceberg table issues for a query.

    Returns Iceberg table name and pre-computed package data if case_number is provided.

    Args:
        query_id: Snowflake query ID
        case_number: Optional Salesforce case number for package data lookup

    Returns:
        Dict with Iceberg table analysis
    """
    try:
        service = TswService()
        result = service.analyze_iceberg(query_id, case_number)

        if not result:
            return {"error": f"No Iceberg table data found for query: {query_id}"}

        return result
    except Exception as e:
        logger.error(f"Error analyzing Iceberg for query {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def analyze_locks(
    deployment: str,
    account_id: int,
    query_id: str,
    case_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze query lock issues.

    Returns queries that were blocking this query and pre-computed package data
    if case_number is provided.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        query_id: Snowflake query ID
        case_number: Optional Salesforce case number for package data lookup

    Returns:
        Dict with lock analysis results
    """
    try:
        service = TswService()
        result = service.analyze_locks(query_id, deployment, account_id, case_number)

        return result
    except Exception as e:
        logger.error(f"Error analyzing locks for query {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def analyze_incidents(case_number: str) -> Dict[str, Any]:
    """
    Analyze incident errors for a case.

    Returns list of query IDs with incident errors and pre-computed package data
    for each query if available.

    Args:
        case_number: Salesforce case number

    Returns:
        Dict with incident analysis results
    """
    try:
        service = TswService()
        result = service.analyze_incidents(case_number)

        return result
    except Exception as e:
        logger.error(f"Error analyzing incidents for case {case_number}: {e}")
        return {"error": str(e)}


@mcp.tool()
def analyze_auth(
    deployment: str,
    account_id: int,
    case_number: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze user authentication issues (SAML/OAUTH).

    Returns SAML/OAUTH integration details, authentication logs if time range provided,
    and pre-computed package data if case_number is provided.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        case_number: Optional Salesforce case number for package data lookup
        start_time: Optional start time for log queries (ISO format)
        end_time: Optional end time for log queries (ISO format)

    Returns:
        Dict with authentication analysis results
    """
    try:
        service = TswService()

        # Convert string dates to datetime if provided
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        result = service.analyze_auth(
            deployment, account_id, case_number, start_dt, end_dt
        )

        if not result:
            return {
                "error": f"No auth data found for deployment {deployment}, account {account_id}"
            }

        return result
    except Exception as e:
        logger.error(f"Error analyzing auth for deployment {deployment}: {e}")
        return {"error": str(e)}


@mcp.tool()
def analyze_rbac(
    deployment: str,
    account_id: int,
    query_id: str,
) -> Dict[str, Any]:
    """
    Analyze RBAC (Role-Based Access Control) issues for a query.

    Returns query details including error information, candidate securables that might
    be causing the issue, user information, and role information if available.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        query_id: Snowflake query ID

    Returns:
        Dict with RBAC analysis results
    """
    try:
        service = TswService()
        result = service.analyze_rbac(query_id, deployment, account_id)

        if not result:
            return {"error": f"No RBAC data found for query: {query_id}"}

        return result
    except Exception as e:
        logger.error(f"Error analyzing RBAC for query {query_id}: {e}")
        return {"error": str(e)}


# ============================================================================
# WAREHOUSES ENDPOINTS (8 tools)
# ============================================================================


@mcp.tool()
def get_warehouse_details(
    deployment: str,
    account_id: int,
    warehouse_name: str,
) -> Dict[str, Any]:
    """
    Get current warehouse configuration and details.

    Returns comprehensive warehouse information including size, type, cluster configuration,
    auto-suspend/resume settings, scaling policy, and timestamps.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        warehouse_name: Warehouse name

    Returns:
        Dict with warehouse details
    """
    try:
        service = WarehouseService()
        details = service.get_warehouse_details(deployment, account_id, warehouse_name)

        if details is None:
            return {
                "error": f"Warehouse not found: {warehouse_name} in account {account_id}"
            }

        return details
    except Exception as e:
        logger.error(f"Error fetching warehouse details: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_warehouse_at_query_time(
    deployment: str,
    account_id: int,
    query_uuid: str,
) -> Dict[str, Any]:
    """
    Get warehouse configuration at the time a specific query ran.

    Returns warehouse settings as they were when the query was executed,
    useful for understanding query performance in context.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        query_uuid: Snowflake query ID

    Returns:
        Dict with warehouse configuration at query time
    """
    try:
        service = WarehouseService()
        details = service.get_warehouse_details_at_query_time(
            deployment, account_id, query_uuid
        )

        if details is None:
            return {
                "error": f"Warehouse configuration not found for query: {query_uuid}"
            }

        return details
    except Exception as e:
        logger.error(f"Error fetching warehouse at query time: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_chart_time_range(
    deployment: str,
    account_id: int,
    warehouse_name: str,
) -> Dict[str, Any]:
    """
    Get start and end timestamps for available chart data.

    Returns the time range for which warehouse chart data is available,
    useful for determining valid date ranges for chart requests.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        warehouse_name: Warehouse name

    Returns:
        Dict with start and end timestamps
    """
    try:
        service = WarehouseService()
        time_range = service.get_chart_time_range(
            deployment, account_id, warehouse_name
        )

        return time_range
    except Exception as e:
        logger.error(f"Error fetching chart time range: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_warehouse_changes(
    deployment: str,
    account_id: int,
    warehouse_name: str,
) -> List[Dict[str, Any]]:
    """
    Get warehouse change history (last 30 days).

    Returns list of configuration changes made to the warehouse including
    event timestamp and type, old and new values, and user who made the change.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        warehouse_name: Warehouse name

    Returns:
        List of warehouse change events
    """
    try:
        service = WarehouseService()
        changes = service.get_change_history(deployment, account_id, warehouse_name)

        return changes
    except Exception as e:
        logger.error(f"Error fetching warehouse changes: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_warehouse_chart_data(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    chart_type: str,
    start_time: str,
    end_time: str,
) -> List[Dict[str, Any]]:
    """
    Get warehouse-level chart data for the specified time range.

    Chart types: EXECUTED_JOBS, ACTIVE_CLUSTERS, XP_RETRY_JOBS, SUCCESS_FAILURE_RATIO

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        warehouse_name: Warehouse name
        chart_type: Chart type (EXECUTED_JOBS, ACTIVE_CLUSTERS, XP_RETRY_JOBS, SUCCESS_FAILURE_RATIO)
        start_time: Start timestamp (ISO format)
        end_time: End timestamp (ISO format)

    Returns:
        List of chart data points
    """
    try:
        service = WarehouseService()

        # Convert string dates to datetime
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        chart_data = service.get_warehouse_chart_data(
            deployment,
            account_id,
            warehouse_name,
            chart_type,
            start_dt,
            end_dt,
        )

        return chart_data
    except ValueError as e:
        logger.error(f"Invalid chart type: {e}")
        return [{"error": str(e)}]
    except Exception as e:
        logger.error(f"Error fetching warehouse chart data: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_cluster_chart_data(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    cluster_num: int,
    chart_type: str,
    start_time: str,
    end_time: str,
) -> List[Dict[str, Any]]:
    """
    Get cluster-level chart data for a specific cluster.

    Chart types: JOB_QUEUE_TRANSITION, JOB_BLOCKED_TRANSITION, QUEUE_TOTAL_TIME, BLOCKED_TOTAL_TIME

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        warehouse_name: Warehouse name
        cluster_num: Cluster number (1-based)
        chart_type: Chart type (JOB_QUEUE_TRANSITION, JOB_BLOCKED_TRANSITION, QUEUE_TOTAL_TIME, BLOCKED_TOTAL_TIME)
        start_time: Start timestamp (ISO format)
        end_time: End timestamp (ISO format)

    Returns:
        List of chart data points
    """
    try:
        service = WarehouseService()

        # Convert string dates to datetime
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        chart_data = service.get_cluster_chart_data(
            deployment,
            account_id,
            warehouse_name,
            cluster_num,
            chart_type,
            start_dt,
            end_dt,
        )

        return chart_data
    except ValueError as e:
        logger.error(f"Invalid chart type: {e}")
        return [{"error": str(e)}]
    except Exception as e:
        logger.error(f"Error fetching cluster chart data: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_event_overlays(
    deployment: str,
    account_id: int,
    warehouse_name: str,
    start_time: str,
    end_time: str,
) -> List[Dict[str, Any]]:
    """
    Get warehouse events for chart overlays within a time range.

    Returns events (configuration changes, parameter overrides, etc.) that can be
    displayed as overlays on warehouse charts.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        warehouse_name: Warehouse name
        start_time: Start timestamp (ISO format)
        end_time: End timestamp (ISO format)

    Returns:
        List of warehouse events
    """
    try:
        service = WarehouseService()

        # Convert string dates to datetime
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        events = service.get_event_overlays(
            deployment,
            account_id,
            warehouse_name,
            start_dt,
            end_dt,
        )

        return events
    except Exception as e:
        logger.error(f"Error fetching event overlays: {e}")
        return [{"error": str(e)}]


# ============================================================================
# ACCOUNTS ENDPOINTS (8 tools)
# ============================================================================


@mcp.tool()
def search_accounts(
    search_query: str,
    deployment: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search for accounts by partial match on locator, alias, or account ID.

    Results are ranked with exact matches first, followed by partial matches.

    Args:
        search_query: Search term for account locator, alias, or ID
        deployment: Optional deployment filter

    Returns:
        List of matching accounts
    """
    try:
        service = AccountService()
        results = service.search_accounts(search_query, deployment)

        return results
    except Exception as e:
        logger.error(f"Error searching accounts: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_account_metadata(
    deployment: str,
    locator: str,
) -> Dict[str, Any]:
    """
    Get comprehensive account metadata.

    Returns detailed information about basic account info (name, alias, account_id),
    service level and account status, version and release groups, load balancer type,
    and cloud provider and region details.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        locator: Account locator

    Returns:
        Dict with account metadata
    """
    try:
        service = AccountService()
        metadata = service.get_account_metadata(deployment, locator)

        if metadata is None:
            return {"error": f"Account not found: {locator} in deployment {deployment}"}

        return metadata
    except Exception as e:
        logger.error(f"Error fetching account metadata: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_release_history(
    deployment: str,
    account_id: int,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get release version history for an account.

    Returns a list of releases with version numbers and timestamps,
    ordered by most recent first.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID
        limit: Maximum number of releases to return (max 500)

    Returns:
        List of releases
    """
    try:
        service = AccountService()
        releases = service.get_release_history(deployment, account_id, min(limit, 500))

        return releases
    except Exception as e:
        logger.error(f"Error fetching release history: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_account_warehouses(
    deployment: str,
    account_id: int,
) -> List[Dict[str, Any]]:
    """
    Get list of warehouses for an account.

    Returns warehouse information including name, size, type,
    provisioning and creation timestamps, and load data availability.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID

    Returns:
        List of warehouses
    """
    try:
        service = AccountService()
        warehouses = service.get_account_warehouses(deployment, account_id)

        return warehouses
    except Exception as e:
        logger.error(f"Error fetching warehouses: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_open_cases(
    deployment: str,
    locator: str,
    alias: str,
) -> List[Dict[str, Any]]:
    """
    Get open Salesforce cases for an account.

    Returns list of open cases with status, category, subcategory, and subject.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        locator: Account locator
        alias: Account alias

    Returns:
        List of open cases
    """
    try:
        service = AccountService()
        cases = service.get_open_cases(deployment, locator, alias)

        return cases
    except Exception as e:
        logger.error(f"Error fetching open cases: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_account_queries(
    deployment: str,
    locator: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get queries executed on this account.

    Returns list of queries with query_id, case_number, timestamp, and SQL hash,
    ordered by most recent first.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        locator: Account locator
        limit: Maximum number of queries to return (max 500)

    Returns:
        List of queries
    """
    try:
        service = AccountService()
        queries = service.get_account_queries(deployment, locator, min(limit, 500))

        return queries
    except Exception as e:
        logger.error(f"Error fetching account queries: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_account_environment(
    deployment: str,
    account_id: int,
) -> Dict[str, str]:
    """
    Get account environment type (prod/dev/test/etc).

    Returns the environment classification for the account.

    Args:
        deployment: Deployment name (e.g., "AWS_US_WEST_2")
        account_id: Account ID

    Returns:
        Dict with environment type
    """
    try:
        service = AccountService()
        environment = service.get_account_environment(deployment, account_id)

        if environment is None:
            return {"error": f"Environment not found for account_id: {account_id}"}

        return {"environment": environment}
    except Exception as e:
        logger.error(f"Error fetching account environment: {e}")
        return {"error": str(e)}


# ============================================================================
# JIRA ENDPOINTS (5 tools)
# ============================================================================


@mcp.tool()
def search_jira_by_query_id(
    query_id: str,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Search JIRA tickets by Snowflake query ID.

    Searches for the query ID in ticket descriptions and summaries.

    Args:
        query_id: Snowflake query ID to search for
        max_results: Maximum results to return (1-100)

    Returns:
        Dict with matching JIRA tickets
    """
    try:
        jira_service = JiraService()
        result = jira_service.search_by_query_id(query_id, max_results=max_results)

        return result.model_dump() if hasattr(result, "model_dump") else result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error searching JIRA by query_id {query_id}: {e}")
        return {"error": str(e)}


@mcp.tool()
def search_jira_by_account(
    account_locator: str,
    status: Optional[List[str]] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Search JIRA tickets by account locator.

    Searches the account locator custom field.

    Args:
        account_locator: Account locator to search for
        status: Optional list of status values to filter by
        max_results: Maximum results to return (1-100)

    Returns:
        Dict with matching JIRA tickets
    """
    try:
        jira_service = JiraService()
        result = jira_service.search_by_account_locator(
            account_locator, status=status, max_results=max_results
        )

        return result.model_dump() if hasattr(result, "model_dump") else result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error searching JIRA by account {account_locator}: {e}")
        return {"error": str(e)}


@mcp.tool()
def search_jira_by_case(
    case_number: str,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Search JIRA tickets by Salesforce case number.

    Searches for case number references in summary, description, and comments.

    Args:
        case_number: Salesforce case number to search for
        max_results: Maximum results to return (1-100)

    Returns:
        Dict with matching JIRA tickets
    """
    try:
        jira_service = JiraService()
        result = jira_service.search_by_case_number(
            case_number, max_results=max_results
        )

        return result.model_dump() if hasattr(result, "model_dump") else result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error searching JIRA by case {case_number}: {e}")
        return {"error": str(e)}


@mcp.tool()
def search_similar_jira_tickets(
    error_message: Optional[str] = None,
    component: Optional[str] = None,
    deployment: Optional[str] = None,
    area: Optional[str] = None,
    days: int = 30,
    similarity_threshold: float = 0.5,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Find similar JIRA tickets based on error message and metadata.

    Uses similarity scoring to find tickets that match the search criteria.
    At least one search criterion must be provided.

    Args:
        error_message: Error message to search for
        component: Component name filter
        deployment: Deployment name filter
        area: JIRA area filter
        days: Search last N days (1-90, default 30)
        similarity_threshold: Minimum similarity score (0-1, default 0.5)
        max_results: Maximum results to return (1-100)

    Returns:
        Dict with similar JIRA tickets
    """
    # Validate at least one criterion provided
    if not any([error_message, component, deployment, area]):
        return {"error": "At least one search criterion must be provided"}

    try:
        jira_service = JiraService()
        result = jira_service.find_similar_tickets(
            error_message=error_message,
            component=component,
            deployment=deployment,
            area=area,
            days=min(days, 90),
            similarity_threshold=max(0.0, min(1.0, similarity_threshold)),
            max_results=max_results,
        )

        return result.model_dump() if hasattr(result, "model_dump") else result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error searching for similar JIRA tickets: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_jira_ticket(ticket_key: str) -> Dict[str, Any]:
    """
    Get a single JIRA ticket by key.

    Args:
        ticket_key: JIRA ticket key (e.g., "SNOW-12345")

    Returns:
        Dict with JIRA ticket details
    """
    try:
        jira_service = JiraService()
        result = jira_service.get_ticket(ticket_key)

        return result.model_dump() if hasattr(result, "model_dump") else result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error fetching JIRA ticket {ticket_key}: {e}")
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
            return {"error": f"Ticket {ticket_key} not found"}
        return {"error": str(e)}


# ============================================================================
# HEALTH CHECK & MAIN
# ============================================================================


@mcp.custom_route("/health", ["GET"])
async def health_check(request):
    """Health check endpoint for Docker health checks"""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "DDA Diagnostic Service (Native)",
        }
    )


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Starting DDA MCP Server (Native Implementation)")
    logger.info("=" * 70)
    logger.info("\nServer details:")
    logger.info("  URL: http://0.0.0.0:8000/mcp")
    logger.info("  Transport: streamable-http")
    logger.info("  Tools: 48 native MCP tools")
    logger.info("\nTool categories:")
    logger.info("  - Cases (3 tools)")
    logger.info("  - Queries (12 tools)")
    logger.info("  - TSW Diagnostics (7 tools)")
    logger.info("  - Warehouses (8 tools)")
    logger.info("  - Accounts (8 tools)")
    logger.info("  - JIRA (5 tools)")
    logger.info("=" * 70)

    # Run the MCP server with streamable-http transport
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
