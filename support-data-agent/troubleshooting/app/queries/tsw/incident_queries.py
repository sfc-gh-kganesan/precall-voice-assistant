"""
Incident Errors Queries

This module contains SQL queries for tracking queries with incident-related errors.
"""

from app.core.table_mappings import get_table_name


class IncidentQueries:
    """SQL queries for incident error tracking."""

    def __init__(self):
        # Find queries with incident errors for a case
        self.get_query_incident_errors_cases = f"""
            SELECT DISTINCT QIM.QUERYID
            FROM CXE.DDA_QUERY_INCIDENT_MAPPING QIM
            INNER JOIN {get_table_name("DDA_CASE_QUERYID_MAPPING_V")} MD
                ON QIM.QUERYID = MD.QUERY_ID
            WHERE TRUE
                AND MD.CASE_NUMBER = %(case_number)s
                AND QIM.INCIDENT_ID IS NOT NULL
            ORDER BY QIM.QUERYID ASC;
        """

        # Check if incident error data exists in package table
        self.get_queryincidenterrors_json_from_tsw_errors_package = """
            -- Check if data exists in TSW_QUERY_ERROR_DATA_PACKAGE table
            SELECT DATA_PACKAGE, _ingestion_timestamp
            FROM TSW_QUERY_ERROR_DATA_PACKAGE
            WHERE case_number = %(case_number)s
                AND query_id = %(queryid)s
            LIMIT 1;
        """
