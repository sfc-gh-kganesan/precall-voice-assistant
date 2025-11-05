"""
Iceberg Table Diagnostics Queries

This module contains SQL queries for diagnosing Iceberg table issues.
"""

from app.core.table_mappings import get_table_name


class IcebergQueries:
    """SQL queries for Iceberg table diagnostics."""

    def __init__(self):
        # Find cases related to Iceberg tables
        self.get_iceberg_query_cases = f"""
            SELECT c.case_number as CASE_NUMBER,
                q.query_id as QUERY_ID,
                q.client_send_time as CLIENT_SEND_TIME,
                q.sql_text as SQL_TEXT,
                q.error_message as ERROR_MESSAGE
            FROM {get_table_name("FDTN_CASE")} c
            INNER JOIN SUPPORT.CXE.FDTN_REL_CASE_QUERY_ID_V q
                ON c.case_number = q.case_number
            WHERE
                (c.SUBJECT ILIKE '%Iceberg%' OR c.DESCRIPTION ILIKE '%Iceberg%')
                AND c.created_date > DATEADD('days', -30, CURRENT_DATE);
        """

        # Get Iceberg table name from logs
        self.get_iceberg_table_name = """
            SELECT OBJECT_MODIFIED_BY_DDL:objectName
            FROM CXE.CXE_TABLE_ACCESS_LOGS_V_LAST_90
            WHERE job_uuid = %(queryid)s;
        """

        # Check if Iceberg data exists in package table
        self.get_iceberg_json_from_tsw_iceberg_package = """
            -- Check if data exists in TSW_ICEBERG_TABLE_DATA_PACKAGE table
            SELECT DATA_PACKAGE, _ingestion_timestamp
            FROM TSW_ICEBERG_TABLE_DATA_PACKAGE
            WHERE case_number = %(casenumber)s
                AND parse_json(QUERY_ID_TABLE_NAME):query_id::string = %(queryid)s
                AND parse_json(QUERY_ID_TABLE_NAME):table_name::string = %(icebergtablename)s
            LIMIT 1;
        """
