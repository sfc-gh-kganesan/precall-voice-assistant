"""
RBAC (Role-Based Access Control) Analysis Queries

This module contains SQL queries for analyzing RBAC permission issues.

Note: RBAC queries are extremely complex. This module implements the core
queries. The full RBAC analysis (user-to-role mappings, privilege changelogs)
can be added later if needed.
"""

from app.core.table_mappings import get_table_name


class RbacQueries:
    """SQL queries for RBAC analysis."""

    def __init__(self):
        # Get query details for RBAC analysis
        self.get_rbac_query_details = f"""
            SELECT
                queryid,
                error_code,
                error_message,
                deployment,
                account_id,
                database_name,
                schema_name,
                role_name,
                user_name,
                sql_text,
                client_send_time
            FROM {get_table_name("DDA_QUERY_METADATA")}
            WHERE queryid = %(queryid)s;
        """

        # Call stored procedure to get candidate securables
        self.get_rbac_candidate_securables = """
            CALL dda_tsw_rbac_candidate_securables_v1(%(queryid)s);
        """

        # Call stored procedure to get securable data
        self.get_rbac_securable_data = """
            CALL dda_tsw_rbac_securables_data_v1(%(queryid)s, %(securable_name)s, %(securable_type)s, %(securable_id)s, %(epoch)s);
        """

        # Find RBAC-related query cases (permission errors)
        self.get_rbac_query_cases = f"""
            SELECT DISTINCT
                MD.CASENUMBER as CASE_NUMBER,
                MD.QUERYID as QUERY_ID,
                MD.ERROR_MESSAGE,
                MD.CLIENT_SEND_TIME
            FROM {get_table_name("DDA_QUERY_METADATA")} MD
            WHERE MD.ERROR_CODE IN (1063, 3001, 3003, 3011, 3041)
            ORDER BY MD.CLIENT_SEND_TIME DESC;
        """

        # Find RBAC user-specific query cases
        self.get_rbac_user_query_cases = f"""
            SELECT DISTINCT
                MD.CASENUMBER as CASE_NUMBER,
                MD.QUERYID as QUERY_ID
            FROM {get_table_name("DDA_QUERY_METADATA")} MD
            WHERE MD.CASENUMBER = %(case_number)s
                AND MD.ERROR_CODE IS NOT NULL
                AND MD.USER_NAME != 'SYSTEM'
                AND (
                    (LOWER(MD.ERROR_MESSAGE) LIKE '%%does not exist%%' OR LOWER(MD.ERROR_MESSAGE) LIKE '%%doesn''''t exist%%')
                    AND LOWER(MD.ERROR_MESSAGE) LIKE '%%not authorized%%'
                )
            ORDER BY QUERY_ID ASC;
        """

    # Dynamic methods for deployment-specific SNOWHOUSE_IMPORT tables
    def get_rbac_user_data(self, deployment: str) -> str:
        """
        Get user data from SNOWHOUSE_IMPORT.

        Args:
            deployment: Snowflake deployment name

        Returns:
            SQL query string
        """
        return f"""
        SELECT
            "ID" AS "USER_ID",
            "NAME" AS "USER_NAME",
            "EMAIL" AS "USER_EMAIL",
            "UPDATED_ON" AS "USER_UPDATED_ON",
            "CREATED_ON" AS "USER_CREATED_ON"
        FROM SNOWHOUSE_IMPORT.{deployment}.USER_RAW_V
        WHERE
            ((("NAME" = %(user_name)s) AND ("ACCOUNT_ID" = %(account_id)s)) AND ("LOAD_TIME" <= TO_TIMESTAMP_NTZ(%(client_send_time)s)))
        ORDER BY
            "UPDATED_ON" DESC NULLS LAST
        LIMIT 1
        """

    def get_rbac_role_data(self, deployment: str) -> str:
        """
        Get role data from SNOWHOUSE_IMPORT.

        Args:
            deployment: Snowflake deployment name

        Returns:
            SQL query string
        """
        return f"""
        SELECT
            "ID" AS "ROLE_ID",
            "NAME" AS "ROLE_NAME",
            "ROLE_TYPE" AS "ROLE_TYPE",
            "UPDATED_ON" AS "ROLE_UPDATED_ON",
            "CREATED_ON" AS "ROLE_CREATED_ON"
        FROM SNOWHOUSE_IMPORT.{deployment}.ROLE_RAW_V
        WHERE
            ((("NAME" = %(role_name)s) AND ("ACCOUNT_ID" = %(account_id)s)) AND ("LOAD_TIME" <= TO_TIMESTAMP_NTZ(%(client_send_time)s)))
        ORDER BY
            "UPDATED_ON" DESC NULLS LAST
        LIMIT 1
        """

    # Note: get_rbac_user_to_role_mapping_data is 600+ lines - omitted for MVP
    # Note: get_rbac_full_account_role_mapping_data is 450+ lines - omitted for MVP
    # Note: get_rbac_privilege_changelog_for_role is 250+ lines - omitted for MVP
    # These can be added later if RBAC analysis requires full role hierarchy
