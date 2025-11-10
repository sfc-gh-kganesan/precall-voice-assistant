"""
Query Service - Business logic for query analysis operations.

This service handles all query-related operations including metadata retrieval,
historical analysis, concurrent query detection, log retrieval, and more.
"""

import logging
from typing import Any, Dict, Optional

from app.queries.query_queries import QueryViewQueries
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class QueryService(BaseService):
    """Service for query analysis operations."""

    def __init__(self):
        super().__init__()
        self.queries = QueryViewQueries()

    def get_query_metadata(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive query metadata including all duration breakdowns.

        Returns detailed information about a query execution including:
        - Basic metadata (account, user, warehouse, etc.)
        - 18+ duration metrics (compilation, execution, queueing, etc.)
        - Resource usage statistics
        - Error information if query failed
        - Performance metrics

        Args:
            query_id: The Snowflake query ID

        Returns:
            Dictionary with query metadata, or None if query not found
        """
        logger.info(f"Fetching metadata for query_id: {query_id}")

        query_sql = self.queries.query_metadata
        params = {"query_id": query_id}

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            logger.warning(f"No metadata found for query_id: {query_id}")
            return None

        # Convert first row to dictionary
        row = result_df.iloc[0].to_dict()

        # Transform to API response format
        return self._transform_query_metadata(row)

    def _transform_query_metadata(self, row: Dict) -> Dict[str, Any]:
        """Transform database row to API response format."""
        return {
            "query_id": row.get("QUERYID"),
            "account_name": row.get("ACCOUNT_NAME"),
            "account_locator": row.get("ACCOUNT_LOCATOR"),
            "sql_text": row.get("SQL_TEXT"),
            "query_hash": row.get("QUERY_HASH"),
            "start_time": row.get("START_TIME").isoformat()
            if row.get("START_TIME")
            else None,
            "end_time": row.get("END_TIME").isoformat()
            if row.get("END_TIME")
            else None,
            "total_duration_ms": row.get("TOTAL_DURATION"),
            "execution_status": row.get("EXECUTION_STATUS"),
            "durations": {
                "compilation_ms": row.get("DUR_COMPILING"),
                "execution_ms": row.get("DUR_XP_EXECUTING"),
                "queued_provisioning_ms": row.get("DUR_QUEUED_PROVISIONING"),
                "queued_repair_ms": row.get("DUR_QUEUED_REPAIR"),
                "queued_overload_ms": row.get("DUR_QUEUED_OVERLOAD"),
                "transaction_blocked_ms": row.get("DUR_TRANSACTION_BLOCKED"),
                "initialization_ms": row.get("DUR_INITIALIZING"),
                "list_external_files_ms": row.get("DUR_LIST_EXTERNAL_FILES"),
            },
            "statistics": {
                "bytes_scanned": row.get("SCANNED_BYTES"),
                "bytes_written": row.get("BYTES_WRITTEN"),
                "bytes_written_to_result": row.get("BYTES_WRITTEN_TO_RESULT"),
                "bytes_read_from_result": row.get("BYTES_READ_FROM_RESULT"),
                "rows_produced": row.get("ROWS_PRODUCED"),
                "rows_inserted": row.get("ROWS_INSERTED"),
                "rows_updated": row.get("ROWS_UPDATED"),
                "rows_deleted": row.get("ROWS_DELETED"),
                "rows_unloaded": row.get("ROWS_UNLOADED"),
                "bytes_deleted": row.get("BYTES_DELETED"),
                "partitions_scanned": row.get("PARTITIONS_SCANNED"),
                "partitions_total": row.get("PARTITIONS_TOTAL"),
                "bytes_spilled_local": row.get("BYTES_SPILLED_TO_LOCAL_STORAGE"),
                "bytes_spilled_remote": row.get("BYTES_SPILLED_TO_REMOTE_STORAGE"),
                "bytes_sent_over_network": row.get("BYTES_SENT_OVER_THE_NETWORK"),
            },
            "warehouse": {
                "name": row.get("WAREHOUSE_NAME"),
                "size": row.get("WAREHOUSE_SIZE"),
                "type": row.get("WAREHOUSE_TYPE"),
                "cluster_number": row.get("CLUSTER_NUMBER"),
            },
            "user": {
                "name": row.get("USER_NAME"),
                "role": row.get("ROLE_NAME"),
            },
            "session": {
                "id": row.get("SESSION_ID"),
                "database": row.get("DATABASE_NAME"),
                "schema": row.get("SCHEMA_NAME"),
            },
            "error": {
                "code": row.get("ERROR_CODE"),
                "message": row.get("ERROR_MESSAGE"),
            }
            if row.get("ERROR_CODE")
            else None,
            "metadata": {
                "query_type": row.get("QUERY_TYPE"),
                "query_tag": row.get("QUERY_TAG"),
                "execution_time": row.get("EXECUTION_TIME"),
                "queued_provisioning_time": row.get("QUEUED_PROVISIONING_TIME"),
                "queued_repair_time": row.get("QUEUED_REPAIR_TIME"),
                "queued_overload_time": row.get("QUEUED_OVERLOAD_TIME"),
                "transaction_blocked_time": row.get("TRANSACTION_BLOCKED_TIME"),
                "outbound_data_transfer_cloud": row.get("OUTBOUND_DATA_TRANSFER_CLOUD"),
                "outbound_data_transfer_region": row.get(
                    "OUTBOUND_DATA_TRANSFER_REGION"
                ),
                "outbound_data_transfer_bytes": row.get("OUTBOUND_DATA_TRANSFER_BYTES"),
                "inbound_data_transfer_cloud": row.get("INBOUND_DATA_TRANSFER_CLOUD"),
                "inbound_data_transfer_region": row.get("INBOUND_DATA_TRANSFER_REGION"),
                "inbound_data_transfer_bytes": row.get("INBOUND_DATA_TRANSFER_BYTES"),
                "credits_used_cloud_services": row.get("CREDITS_USED_CLOUD_SERVICES"),
                "release_version": row.get("RELEASE_VERSION"),
                "external_function_total_invocations": row.get(
                    "EXTERNAL_FUNCTION_TOTAL_INVOCATIONS"
                ),
                "external_function_total_sent_rows": row.get(
                    "EXTERNAL_FUNCTION_TOTAL_SENT_ROWS"
                ),
                "external_function_total_received_rows": row.get(
                    "EXTERNAL_FUNCTION_TOTAL_RECEIVED_ROWS"
                ),
                "external_function_total_sent_bytes": row.get(
                    "EXTERNAL_FUNCTION_TOTAL_SENT_BYTES"
                ),
                "external_function_total_received_bytes": row.get(
                    "EXTERNAL_FUNCTION_TOTAL_RECEIVED_BYTES"
                ),
            },
        }

    def get_historical_runs(self, query_id: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Get historical runs of queries with the same SQL hash.

        Args:
            query_id: The Snowflake query ID
            limit: Maximum number of historical runs to return

        Returns:
            Dictionary with historical runs data
        """
        logger.info(
            f"Fetching historical runs for query_id: {query_id}, limit: {limit}"
        )

        query_sql = self.queries.get_historical_runs
        params = {"query_id": query_id, "limit": limit}

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            return {"query_id": query_id, "historical_runs": [], "count": 0}

        # Convert DataFrame to list of dictionaries
        runs = result_df.to_dict(orient="records")

        return {
            "query_id": query_id,
            "historical_runs": runs,
            "count": len(runs),
        }

    def get_concurrent_queries(
        self, query_id: str, cluster_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get queries that ran concurrently in the same warehouse.

        Args:
            query_id: The Snowflake query ID
            cluster_number: Optional cluster number to filter by

        Returns:
            Dictionary with concurrent queries data
        """
        logger.info(
            f"Fetching concurrent queries for query_id: {query_id}, cluster: {cluster_number}"
        )

        query_sql = self.queries.get_concurrent_queries
        params = {"query_id": query_id}
        if cluster_number is not None:
            params["cluster_number"] = cluster_number

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            return {"query_id": query_id, "concurrent_queries": [], "count": 0}

        # Convert DataFrame to list of dictionaries
        queries = result_df.to_dict(orient="records")

        return {
            "query_id": query_id,
            "cluster_number": cluster_number,
            "concurrent_queries": queries,
            "count": len(queries),
        }

    def get_gs_logs(self, query_id: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Get Global Services (GS) logs for a query.

        Args:
            query_id: The Snowflake query ID
            limit: Maximum number of log entries to return

        Returns:
            Dictionary with GS logs data
        """
        logger.info(f"Fetching GS logs for query_id: {query_id}, limit: {limit}")

        # First, get query metadata to extract deployment info
        metadata_query = self.queries.query_metadata
        metadata_result = self.execute_query(
            metadata_query, {"query_id": query_id}, use_cache=True
        )

        if metadata_result.empty:
            logger.warning(f"No metadata found for query_id: {query_id}")
            return {"query_id": query_id, "logs": [], "count": 0}

        # Extract deployment from metadata
        deployment = metadata_result.iloc[0].get("DEPLOYMENT")
        if not deployment:
            logger.warning(f"No deployment found in metadata for query_id: {query_id}")
            return {"query_id": query_id, "logs": [], "count": 0}

        query_sql = self.queries.get_gs_logs()
        params = {"query_id": query_id, "deployment": deployment, "limit": limit}

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            return {"query_id": query_id, "logs": [], "count": 0}

        # Convert DataFrame to list of dictionaries
        logs = result_df.to_dict(orient="records")

        return {
            "query_id": query_id,
            "log_type": "GS",
            "logs": logs,
            "count": len(logs),
        }

    def get_xp_logs(self, query_id: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Get Execution Platform (XP) logs for a query.

        Args:
            query_id: The Snowflake query ID
            limit: Maximum number of log entries to return

        Returns:
            Dictionary with XP logs data
        """
        logger.info(f"Fetching XP logs for query_id: {query_id}, limit: {limit}")

        query_sql = self.queries.get_xp_logs()
        params = {"query_id": query_id, "limit": limit}

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            return {"query_id": query_id, "logs": [], "count": 0}

        # Convert DataFrame to list of dictionaries
        logs = result_df.to_dict(orient="records")

        return {
            "query_id": query_id,
            "log_type": "XP",
            "logs": logs,
            "count": len(logs),
        }

    def get_parameters(self, query_id: str) -> Dict[str, Any]:
        """
        Get non-default parameters for a query.

        Args:
            query_id: The Snowflake query ID

        Returns:
            Dictionary with parameters data
        """
        logger.info(f"Fetching parameters for query_id: {query_id}")

        query_sql = self.queries.get_parameters
        params = {"query_id": query_id}

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            return {"query_id": query_id, "parameters": [], "count": 0}

        # Convert DataFrame to list of dictionaries
        parameters = result_df.to_dict(orient="records")

        return {
            "query_id": query_id,
            "parameters": parameters,
            "count": len(parameters),
        }

    def get_incidents(self, query_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Get incidents from Crash Manager for a query.

        Args:
            query_id: The Snowflake query ID
            limit: Maximum number of incidents to return

        Returns:
            Dictionary with incidents data
        """
        logger.info(f"Fetching incidents for query_id: {query_id}, limit: {limit}")

        query_sql = self.queries.get_incidents
        params = {"query_id": query_id, "limit": limit}

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            return {"query_id": query_id, "incidents": [], "count": 0}

        # Convert DataFrame to list of dictionaries
        incidents = result_df.to_dict(orient="records")

        return {
            "query_id": query_id,
            "incidents": incidents,
            "count": len(incidents),
        }

    def get_parent_child_tree(self, query_id: str) -> Dict[str, Any]:
        """
        Get parent-child query execution tree.

        Args:
            query_id: The Snowflake query ID

        Returns:
            Dictionary with parent-child tree data
        """
        logger.info(f"Fetching parent-child tree for query_id: {query_id}")

        query_sql = self.queries.get_parent_child_tree
        params = {"query_id": query_id}

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            return {"query_id": query_id, "tree": [], "count": 0}

        # Convert DataFrame to list of dictionaries
        tree = result_df.to_dict(orient="records")

        return {
            "query_id": query_id,
            "tree": tree,
            "count": len(tree),
        }

    def get_processing_status(self, query_id: str) -> Dict[str, Any]:
        """
        Get DDA pipeline processing status (0-100%).

        Args:
            query_id: The Snowflake query ID

        Returns:
            Dictionary with processing status
        """
        logger.info(f"Fetching processing status for query_id: {query_id}")

        query_sql = self.queries.get_query_process_status
        params = {"query_id": query_id}

        result_df = self.execute_query(query_sql, params, use_cache=True)

        if result_df.empty:
            return {
                "query_id": query_id,
                "status": "not_found",
                "percentage": 0,
            }

        row = result_df.iloc[0].to_dict()

        return {
            "query_id": query_id,
            "status": row.get("STATUS", "unknown"),
            "percentage": row.get("PERCENTAGE", 0),
            "last_updated": row.get("LAST_UPDATED").isoformat()
            if row.get("LAST_UPDATED")
            else None,
        }

    def trigger_adhoc_process(
        self, query_id: str, case_number: str, user_email: str
    ) -> Dict[str, Any]:
        """
        Trigger adhoc DDA pipeline processing.

        Args:
            query_id: The Snowflake query ID
            case_number: The case number
            user_email: Email of user triggering the process

        Returns:
            Dictionary with job status
        """
        logger.info(
            f"Triggering adhoc process for query_id: {query_id}, case: {case_number}, user: {user_email}"
        )

        # Call stored procedure to trigger adhoc processing
        query_sql = self.queries.trigger_adhoc_processing
        params = {
            "query_id": query_id,
            "case_number": case_number,
            "user_email": user_email,
        }

        # Use WRITE connection for stored procedure calls
        result_df = self.execute_query(
            query_sql, params, use_cache=False, connection_type="QUERY_CATALOG"
        )

        if result_df.empty:
            return {
                "query_id": query_id,
                "status": "failed",
                "message": "Failed to trigger adhoc processing",
            }

        row = result_df.iloc[0].to_dict()

        return {
            "query_id": query_id,
            "case_number": case_number,
            "status": "success",
            "job_id": row.get("JOB_ID"),
            "message": "Adhoc processing triggered successfully",
        }

    def compare_queries(self, query_id_1: str, query_id_2: str) -> Dict[str, Any]:
        """
        Compare two queries (metadata, parameters, performance).

        Args:
            query_id_1: First query ID
            query_id_2: Second query ID

        Returns:
            Dictionary with comparison data
        """
        logger.info(f"Comparing queries: {query_id_1} vs {query_id_2}")

        # Fetch metadata for both queries
        metadata_1 = self.get_query_metadata(query_id_1)
        metadata_2 = self.get_query_metadata(query_id_2)

        if not metadata_1 or not metadata_2:
            return {
                "error": "One or both queries not found",
                "query_id_1": query_id_1,
                "query_id_2": query_id_2,
            }

        # Calculate differences
        comparison = {
            "query_id_1": query_id_1,
            "query_id_2": query_id_2,
            "metadata": {
                "query_1": metadata_1,
                "query_2": metadata_2,
            },
            "performance_diff": {
                "total_duration_ms": metadata_2["total_duration_ms"]
                - metadata_1["total_duration_ms"],
                "compilation_ms": metadata_2["durations"]["compilation_ms"]
                - metadata_1["durations"]["compilation_ms"],
                "execution_ms": metadata_2["durations"]["execution_ms"]
                - metadata_1["durations"]["execution_ms"],
            },
            "resource_diff": {
                "bytes_scanned": metadata_2["statistics"]["bytes_scanned"]
                - metadata_1["statistics"]["bytes_scanned"],
                "rows_produced": metadata_2["statistics"]["rows_produced"]
                - metadata_1["statistics"]["rows_produced"],
            },
        }

        return comparison
