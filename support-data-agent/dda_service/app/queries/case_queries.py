"""
Case Queries

This module contains SQL queries for case-related operations.
"""

from app.core.table_mappings import get_table_name


class CaseQueries:
    """SQL queries for case operations."""

    def __init__(self):
        # Get case metadata from FDTN_CASE view
        self.get_case_metadata = f"""
            SELECT
                c.ID,
                c.CASE_NUMBER,
                c.SUBJECT,
                c.STATUS,
                c.ORIGIN,
                c.TYPE,
                c.CATEGORY_C,
                c.SUB_CATEGORY_C,
                c.SEVERITY_C,
                c.ROOT_CAUSE_C,
                c.CREATED_DATE,
                c.LAST_MODIFIED_DATE,
                c.IS_CLOSED,
                c.IS_ESCALATED,
                c.IS_DELETED,
                c.CASE_OWNER_NAME_C,
                c.OWNER_ID,
                c.SFDC_ACCOUNT_ID,
                c.DESCRIPTION,
                c.CLOUD,
                c.REGION,
                c.SNOWFLAKE_ACCOUNT_ALIAS,
                c.SNOWFLAKE_ACCOUNT_LOCATOR,
                c.RECORD_TYPE_ID,
                c._INGESTION_TIMESTAMP
            FROM {get_table_name("FDTN_CASE")} c
            WHERE c.CASE_NUMBER = %(case_number)s
            LIMIT 1;
        """

        # Get queries associated with a case
        self.get_case_queries = f"""
            WITH case_query_map AS (
                -- Primary source: DDA case mapping
                SELECT DISTINCT
                    QUERY_ID as QUERYID,
                    CASE_NUMBER
                FROM {get_table_name("DDA_CASE_QUERYID_MAPPING_V")}
                WHERE CASE_NUMBER = %(case_number)s

                UNION

                -- Adhoc query relations
                SELECT DISTINCT
                    QUERY_ID as QUERYID,
                    RELATION_VALUE AS CASE_NUMBER
                FROM {get_table_name("DDA_ADHOC_QUERY_ID_RELATION")}
                WHERE RELATION_TYPE = 'CASE_NUMBER'
                  AND RELATION_VALUE = %(case_number)s

                UNION

                -- Query metadata direct mapping
                SELECT DISTINCT
                    QUERYID,
                    CASENUMBER as CASE_NUMBER
                FROM {get_table_name("DDA_QUERY_METADATA")}
                WHERE CASENUMBER = %(case_number)s
            )
            SELECT
                cqm.QUERYID,
                md.sql_text,
                md.client_send_time,
                md.end_time,
                md.error_code,
                md.error_message,
                md.warehouse_name,
                md.user_name,
                md.database_name,
                md.deployment,
                md.account_id,
                md.account_name
            FROM case_query_map cqm
            LEFT JOIN {get_table_name("DDA_QUERY_METADATA")} md
                ON cqm.QUERYID = md.queryid
            ORDER BY md.client_send_time DESC;
        """

        # Search cases by various criteria
        self.search_cases = f"""
            SELECT
                c.CASE_NUMBER,
                c.SUBJECT,
                c.STATUS,
                c.CATEGORY_C,
                c.SUB_CATEGORY_C,
                c.SEVERITY_C,
                c.CREATED_DATE,
                c.LAST_MODIFIED_DATE,
                c.IS_CLOSED,
                c.IS_ESCALATED,
                c.CASE_OWNER_NAME_C,
                c.SFDC_ACCOUNT_ID,
                c.SNOWFLAKE_ACCOUNT_ALIAS
            FROM {get_table_name("FDTN_CASE")} c
            WHERE 1=1
                AND (%(status)s IS NULL OR c.STATUS = %(status)s)
                AND (%(is_closed)s IS NULL OR c.IS_CLOSED = %(is_closed)s)
                AND (%(functional_area)s IS NULL OR c.CATEGORY_C = %(functional_area)s)
                AND (%(start_date)s IS NULL OR c.CREATED_DATE >= %(start_date)s)
                AND (%(end_date)s IS NULL OR c.CREATED_DATE <= %(end_date)s)
            ORDER BY c.CREATED_DATE DESC
            LIMIT %(limit)s;
        """

        # Get case query count
        self.get_case_query_count = f"""
            WITH case_query_map AS (
                SELECT DISTINCT QUERY_ID as QUERYID
                FROM {get_table_name("DDA_CASE_QUERYID_MAPPING_V")}
                WHERE CASE_NUMBER = %(case_number)s

                UNION

                SELECT DISTINCT QUERY_ID as QUERYID
                FROM {get_table_name("DDA_ADHOC_QUERY_ID_RELATION")}
                WHERE RELATION_TYPE = 'CASE_NUMBER'
                  AND RELATION_VALUE = %(case_number)s

                UNION

                SELECT DISTINCT QUERYID
                FROM {get_table_name("DDA_QUERY_METADATA")}
                WHERE CASENUMBER = %(case_number)s
            )
            SELECT COUNT(*) as QUERY_COUNT
            FROM case_query_map;
        """
