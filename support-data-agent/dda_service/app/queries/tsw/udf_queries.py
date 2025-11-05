"""
UDF (User-Defined Functions) Analysis Queries

This module contains SQL queries for analyzing UDF usage in queries.
"""

from app.core.table_mappings import get_table_name


class UdfQueries:
    """SQL queries for UDF analysis."""

    def __init__(self):
        # Find cases with UDF usage
        self.get_tsw_case_with_udf_metadata = f"""
            -- TSW on case page - Find cases with UDF usage
            SELECT DISTINCT
                C.CASE_NUMBER AS "CASE NUMBER",
                Q.QUERY_ID AS "QUERY ID"
            FROM {get_table_name("FDTN_CASE")} C
            JOIN {get_table_name("DDA_CASE_QUERYID_MAPPING_V")} Q
                ON C.CASE_NUMBER = Q.CASE_NUMBER
            JOIN {get_table_name("DDA_QUERY_METADATA")} MD
                ON Q.QUERY_ID = MD.QUERYID
            JOIN {get_table_name("DDA_REL_QUERY_ID_GS_LOGS")} GS
                ON Q.QUERY_ID = GS.JOB_UUID
                AND GS.CLASS = 'com.snowflake.services.usagetracking.TableColumnInfoTracker'
                AND GS.MESSAGE LIKE '%udf%'
            ORDER BY C.CASE_NUMBER DESC;
        """

        # Get query metadata for UDF analysis
        self.get_queryid_metadata = f"""
            SELECT
                md.queryid,
                md.sql_text,
                md.error_code,
                md.error_message,
                md.warehouse_name,
                md.warehouse_size,
                md.latest_cluster_number + 1 as latest_cluster_number,
                md.client_send_time
            FROM {get_table_name("DDA_QUERY_METADATA")} md
            WHERE md.queryid = %(queryid)s;
        """

        # Call stored procedure to get UDF JSON data
        self.get_udf_json = """
            CALL SUPPORT.CXE.DDA_TSW_UDF_JSON(%(queryid)s, 15);
        """

        # Get table objects accessed by the query (used for UDF analysis)
        self.get_table_objects = f"""
            SELECT DISTINCT
                t.value : name::varchar as table_name,
                t.value : id::varchar as table_id,
                t.value : version::varchar as table_version,
                t.value : files::int as table_file_num,
                t.value : rows::int as table_row_num,
                t.value : isDmlTarget::boolean as isDmlTarget,
                t.value : isExternal::boolean as isExternal,
                t.value : isHybrid::boolean as isHybrid,
                t.value : isMV::boolean as isMV,
                t.value : isTemp::boolean as isTemp
            FROM
                {get_table_name("DDA_QUERY_METADATA")} md
            JOIN {get_table_name("DDA_REL_QUERY_ID_GS_LOGS")} gl
                ON (md.queryid = gl.job_uuid
                    AND md.account_id = gl.account_id
                    AND md.deployment = gl.deployment
                    AND md.gs_cluster_name = gl.gs_cluster
                    AND md.gs_inst_id = gl.gs_id),
            LATERAL flatten (
                parse_json(
                    replace(MESSAGE, 'Table and column accesses: ')
                ): tables
            ) t
            WHERE TRUE
                AND md.QUERYID = %(queryid)s
                AND gl.CLASS = 'com.snowflake.services.usagetracking.TableColumnInfoTracker'
            ORDER BY TABLE_ID, TABLE_VERSION;
        """
