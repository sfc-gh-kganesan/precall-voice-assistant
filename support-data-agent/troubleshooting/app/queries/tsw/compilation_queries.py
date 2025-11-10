"""
Query Compilation Analysis Queries

This module contains SQL queries for analyzing query compilation performance issues.
"""

from app.core.table_mappings import get_table_name


class CompilationQueries:
    """SQL queries for query compilation analysis."""

    def __init__(self):
        # Find queries with high compilation time
        self.get_case_queryid = """
            WITH filtered_jobs AS (
                SELECT uuid, dur_xp_executing, dur_compiling, total_duration
                FROM cxe.cxe_job_raw_v_last_90
                WHERE
                    account_id = %(account_id)s
                    AND deployment = %(deployment)s
                    AND uuid IN (%(query_ids)s)
            )
            SELECT *
            FROM filtered_jobs
            WHERE dur_compiling >= 0.15 * dur_xp_executing
                OR dur_compiling > 10000;
        """

        # Get query metadata for compilation analysis
        self.get_query_comp_metadata = f"""
            SELECT queryid, account_id, deployment
            FROM {get_table_name("DDA_QUERY_METADATA")}
            WHERE casenumber = %(casenumber)s;
        """

        # Check if compilation data exists in package table
        self.get_querycomp_json_from_tsw_compilation_package = """
            -- Check if data exists in TSW_QUERY_COMPILATION_DATA_PACKAGE table
            SELECT DATA_PACKAGE, _ingestion_timestamp
            FROM TSW_QUERY_COMPILATION_DATA_PACKAGE
            WHERE case_number = %(casenumber)s
                AND query_id = %(queryid)s
            LIMIT 1;
        """

        # Get duration values for compilation analysis
        self.get_querycomp_dur_vals = """
            SELECT
                dur_xp_executing,
                dur_compiling,
                total_duration
            FROM cxe.cxe_job_raw_v_last_90
            WHERE uuid = %(queryid)s;
        """
