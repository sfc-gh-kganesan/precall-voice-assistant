"""
Query Locks Analysis Queries

This module contains SQL queries for analyzing transaction lock issues.
"""

from app.core.table_mappings import get_table_name


class LocksQueries:
    """SQL queries for query lock analysis."""

    def __init__(self):
        # Find cases with query lock issues
        self.get_query_lock_cases = f"""
            SELECT DISTINCT
                MD.CASENUMBER as CASE_NUMBER,
                MD.QUERYID as QUERYID
            FROM {get_table_name("DDA_QUERY_METADATA")} MD
            JOIN {get_table_name("DDA_QUERY_HISTORICAL_RUN_STATS")} H
                ON (H.CURRENT_QUERYID = MD.QUERYID
                    AND H.CURRENT_QUERYID = H.OTHER_QUERYID
                    AND H.CLIENT_SEND_TIME = MD.CLIENT_SEND_TIME)
            WHERE H.DUR_TXN_LOCK > 0
            ORDER BY CASE_NUMBER DESC;
        """

        # Check if lock data exists in package table
        self.get_querylock_json_from_tsw_locks_package = """
            -- Check if data exists in TSW_QUERY_LOCKS_DATA_PACKAGE table
            SELECT DATA_PACKAGE, _ingestion_timestamp
            FROM TSW_QUERY_LOCKS_DATA_PACKAGE
            WHERE case_number = %(casenumber)s
                AND query_id = %(queryid)s
            LIMIT 1;
        """

    # Dynamic method for deployment-specific SNOWHOUSE_IMPORT table
    def get_locking_queries_md(self, deployment: str) -> str:
        """
        Get locking query metadata from SNOWHOUSE_IMPORT.

        Args:
            deployment: Snowflake deployment name

        Returns:
            SQL query string
        """
        return f"""
            SELECT
                concat_ws('.', lock_object_database_name, lock_object_schema_name, lock_object_name) AS full_lock_object_name,
                lock_object_type,
                user_name,
                lock_event_time,
                blocker_queries_internal,
                q.value:query_id::varchar AS query_id
            FROM SNOWHOUSE_IMPORT.{deployment}.LOCK_WAIT_HISTORY_V,
                 LATERAL FLATTEN(try_parse_json(blocker_queries)) q
            WHERE query_id IN (%(queryid)s)
              AND lock_event = 'LOCK_WAIT'
              AND account_id = %(account_id)s;
        """
