"""
CRITICAL: Table/View Mappings for Environment-Based Data Access
================================================================

This module provides environment-specific table/view mappings to ensure
proper data masking in dev/local environments while using production tables
in prod/canary environments.

SECURITY: In dev/local, all customer data tables are mapped to masked views
to protect sensitive customer information.
"""

from app.config import settings


# Dev environment mapping - maps production tables to masked views
DEV_VIEW_MAPPING = {
    "DDA_AUTHENTICATION_AGGS": "DDA_AUTHENTICATION_AGGS_MASKED_V",
    "DDA_JOB_AGGS": "DDA_JOB_AGGS_MASKED_V",
    "DDA_NEW_QUERY_SET": "DDA_NEW_QUERY_SET_MASKED_V",
    "DDA_QUERY_HISTORICAL_RUN_STATS": "DDA_QUERY_HISTORICAL_RUN_STATS_MASKED_V",
    "DDA_QUERY_METADATA": "DDA_QUERY_METADATA_MASKED_V",
    "DDA_QUERY_WAREHOUSE_STATS": "DDA_QUERY_WAREHOUSE_STATS_MASKED_V",
    "DDA_REL_PARAMETER_OVERRIDE_VALUE_LATEST_CHANGES": "DDA_REL_PARAMETER_OVERRIDE_VALUE_LATEST_CHANGES_MASKED_V",
    "DDA_REL_NON_DEFAULT_PARAMETER_QUERY_ID": "DDA_REL_NON_DEFAULT_PARAMETER_QUERY_ID_MASKED_V",
    "DDA_REL_QUERY_ID_GS_LOGS": "DDA_REL_QUERY_ID_GS_LOGS_MASKED_V",
    "DDA_REL_QUERY_ID_XP_LOGS": "DDA_REL_QUERY_ID_XP_LOGS_MASKED_V",
    "FDTN_SNWFLK_ACCOUNT": "FDTN_SNWFLK_ACCOUNT_MASKED_V",
    "FDTN_SALESFORCE_ACCOUNT": "FDTN_SALESFORCE_ACCOUNT_MASKED_V",
    "DDA_ADHOC_QUERY_STAGING_TABLE": "DDA_ADHOC_QUERY_STAGING_TABLE_MASKED_V",
    "FDTN_CASE": "FDTN_CASE_MASKED_V",
    # Tables without customer data - safe to use directly in dev
    "DDA_QUERY_FILTER": "DDA_QUERY_FILTER",
    "DDA_QUERY_INCIDENT_MAPPING": "DDA_QUERY_INCIDENT_MAPPING",
    "DDA_REL_PARAMETER_QUERY_ID": "DDA_REL_PARAMETER_QUERY_ID",
    "DDA_REL_QUERY_GS_ERROR_LOGS": "DDA_REL_QUERY_GS_ERROR_LOGS",
    "DDA_REL_QUERY_ID_GRAPH_JSON": "DDA_REL_QUERY_ID_GRAPH_JSON",
    "DDA_REL_QUERY_XP_ERROR_LOGS": "DDA_REL_QUERY_XP_ERROR_LOGS",
    "DDA_ACCOUNT_EXTENDED_PROPERTIES_HISTORY": "DDA_ACCOUNT_EXTENDED_PROPERTIES_HISTORY",
    "DDA_CASE_QUERYID_MAPPING_V": "DDA_CASE_QUERYID_MAPPING_V",
    # New tables for Account Service (non-customer data)
    "DDA_RELEASE_VERSION_HISTORY": "DDA_RELEASE_VERSION_HISTORY",
    "FDTN_WAREHOUSE_METADATA": "FDTN_WAREHOUSE_METADATA",
    "DDA_REL_WH_LOAD_QUERY_SEC_SLICE": "DDA_REL_WH_LOAD_QUERY_SEC_SLICE",
    "FDTN_WAREHOUSE_EVENTS_LAST_30": "FDTN_WAREHOUSE_EVENTS_LAST_30",
    "DDA_REL_SF_PS_ACCOUNT_SNFL_ACCOUNT_DEPLOYMENT_V": "DDA_REL_SF_PS_ACCOUNT_SNFL_ACCOUNT_DEPLOYMENT_V",
    "CXE_DEPLOYMENT_MAPPING_V": "CXE_DEPLOYMENT_MAPPING_V",
    # TSW-specific tables
    "CXE_TABLE_ACCESS_LOGS_V_LAST_90": "CXE_TABLE_ACCESS_LOGS_V_LAST_90",
    "dda_rel_acc_md_saml_integration_v": "dda_rel_acc_md_saml_integration_v",
}


def get_table_name(table_name: str) -> str:
    """
    Get environment-appropriate table or view name.

    In dev/local environments, returns masked view names for tables with customer data.
    In prod/canary environments, returns original table names.

    Args:
        table_name: Base table name (e.g., "DDA_QUERY_METADATA")

    Returns:
        str: Environment-appropriate table or view name

    Raises:
        ValueError: If table_name is not in DEV_VIEW_MAPPING and environment is dev/local

    Examples:
        >>> # In dev environment
        >>> get_table_name("DDA_QUERY_METADATA")
        'DDA_QUERY_METADATA_MASKED_V'

        >>> # In prod environment
        >>> get_table_name("DDA_QUERY_METADATA")
        'DDA_QUERY_METADATA'
    """
    if settings.ENV in ["dev", "local", "local_dev"]:
        if table_name not in DEV_VIEW_MAPPING:
            raise ValueError(
                f"Dev View not found for table '{table_name}'. "
                f"All tables must be mapped in DEV_VIEW_MAPPING for security."
            )
        return DEV_VIEW_MAPPING[table_name]
    else:
        # prod, canary - use production tables
        return table_name


def get_table_mappings() -> dict:
    """
    Get all table/view mappings as a dictionary for SQL parameter substitution.

    Returns a dictionary mapping parameter names (used in SQL) to actual table/view names
    based on the current environment. This is used to populate SQL parameters like
    %(query_metadata_view_or_table)s with the correct table or masked view name.

    Returns:
        dict: Mapping of SQL parameter names to table/view names

    Examples:
        >>> mappings = get_table_mappings()
        >>> mappings['query_metadata_view_or_table']  # In prod
        'DDA_QUERY_METADATA'
        >>> mappings['query_metadata_view_or_table']  # In dev
        'DDA_QUERY_METADATA_MASKED_V'
    """
    return {
        # Query metadata and history
        "query_metadata_view_or_table": get_table_name("DDA_QUERY_METADATA"),
        "QUERY_METADATA_VIEW_OR_TABLE": get_table_name("DDA_QUERY_METADATA"),
        "historical_run_view_or_table": get_table_name(
            "DDA_QUERY_HISTORICAL_RUN_STATS"
        ),
        "HISTORICAL_RUN_VIEW_OR_TABLE": get_table_name(
            "DDA_QUERY_HISTORICAL_RUN_STATS"
        ),
        "dda_historical_run_stats": get_table_name("DDA_QUERY_HISTORICAL_RUN_STATS"),
        "warehouse_stats_view_or_table": get_table_name("DDA_QUERY_WAREHOUSE_STATS"),
        "WAREHOUSE_STATS_VIEW_OR_TABLE": get_table_name("DDA_QUERY_WAREHOUSE_STATS"),
        "dda_query_warehouse_stats": get_table_name("DDA_QUERY_WAREHOUSE_STATS"),
        # Parameters and configuration
        "rel_non_default_parameter_query_id_view_or_table": get_table_name(
            "DDA_REL_NON_DEFAULT_PARAMETER_QUERY_ID"
        ),
        "REL_NON_DEFAULT_PARAMETER_QUERY_ID_VIEW_OR_TABLE": get_table_name(
            "DDA_REL_NON_DEFAULT_PARAMETER_QUERY_ID"
        ),
        # Logs
        "rel_query_id_gs_logs_view_or_table": get_table_name(
            "DDA_REL_QUERY_ID_GS_LOGS"
        ),
        "REL_QUERY_ID_GS_LOGS_VIEW_OR_TABLE": get_table_name(
            "DDA_REL_QUERY_ID_GS_LOGS"
        ),
        "rel_query_id_xp_logs_view_or_table": get_table_name(
            "DDA_REL_QUERY_ID_XP_LOGS"
        ),
        "REL_QUERY_ID_XP_LOGS_VIEW_OR_TABLE": get_table_name(
            "DDA_REL_QUERY_ID_XP_LOGS"
        ),
        # Foundation tables
        "fdtn_snwflk_account": get_table_name("FDTN_SNWFLK_ACCOUNT"),
        "FDTN_SNWFLK_ACCOUNT": get_table_name("FDTN_SNWFLK_ACCOUNT"),
        "FDTN_SALESFORCE_ACCOUNT": get_table_name("FDTN_SALESFORCE_ACCOUNT"),
        "FDTN_CASE": get_table_name("FDTN_CASE"),
        "fdtn_case": get_table_name("FDTN_CASE"),
        # Other tables
        "AUTHENTICATION_AGGS_VIEW_OR_TABLE": get_table_name("DDA_AUTHENTICATION_AGGS"),
        "authentication_aggs_view_or_table": get_table_name("DDA_AUTHENTICATION_AGGS"),
        "JOB_AGGS_VIEW_OR_TABLE": get_table_name("DDA_JOB_AGGS"),
        "job_aggs_view_or_table": get_table_name("DDA_JOB_AGGS"),
        "NEW_QUERY_SET_VIEW_OR_TABLE": get_table_name("DDA_NEW_QUERY_SET"),
        "DDA_ADHOC_QUERY_STAGING_TABLE": get_table_name(
            "DDA_ADHOC_QUERY_STAGING_TABLE"
        ),
        "DDA_ACCOUNT_EXTENDED_PROPERTIES_HISTORY": get_table_name(
            "DDA_ACCOUNT_EXTENDED_PROPERTIES_HISTORY"
        ),
        "dda_account_extended_properties_history": get_table_name(
            "DDA_ACCOUNT_EXTENDED_PROPERTIES_HISTORY"
        ),
    }


# Commonly used table name constants
# These use get_table_name() to automatically apply environment mapping
class Tables:
    """Centralized table name constants with automatic environment mapping"""

    @staticmethod
    def authentication_aggs() -> str:
        return get_table_name("DDA_AUTHENTICATION_AGGS")

    @staticmethod
    def fdtn_snwflk_account() -> str:
        return get_table_name("FDTN_SNWFLK_ACCOUNT")

    @staticmethod
    def fdtn_salesforce_account() -> str:
        return get_table_name("FDTN_SALESFORCE_ACCOUNT")

    @staticmethod
    def job_aggs() -> str:
        return get_table_name("DDA_JOB_AGGS")

    @staticmethod
    def historical_run_stats() -> str:
        return get_table_name("DDA_QUERY_HISTORICAL_RUN_STATS")

    @staticmethod
    def new_query_set() -> str:
        return get_table_name("DDA_NEW_QUERY_SET")

    @staticmethod
    def query_incident_mapping() -> str:
        return get_table_name("DDA_QUERY_INCIDENT_MAPPING")

    @staticmethod
    def query_metadata() -> str:
        return get_table_name("DDA_QUERY_METADATA")

    @staticmethod
    def case_queryid_mapping() -> str:
        return get_table_name("DDA_CASE_QUERYID_MAPPING_V")

    @staticmethod
    def rel_non_default_parameter_query_id() -> str:
        return get_table_name("DDA_REL_NON_DEFAULT_PARAMETER_QUERY_ID")

    @staticmethod
    def rel_parameter_override_value_latest_changes() -> str:
        return get_table_name("DDA_REL_PARAMETER_OVERRIDE_VALUE_LATEST_CHANGES")

    @staticmethod
    def rel_query_id_gs_logs() -> str:
        return get_table_name("DDA_REL_QUERY_ID_GS_LOGS")

    @staticmethod
    def rel_query_id_xp_logs() -> str:
        return get_table_name("DDA_REL_QUERY_ID_XP_LOGS")

    @staticmethod
    def warehouse_stats() -> str:
        return get_table_name("DDA_QUERY_WAREHOUSE_STATS")

    @staticmethod
    def adhoc_query_staging() -> str:
        return get_table_name("DDA_ADHOC_QUERY_STAGING_TABLE")

    @staticmethod
    def fdtn_case() -> str:
        return get_table_name("FDTN_CASE")

    @staticmethod
    def account_extended_properties_history() -> str:
        return get_table_name("DDA_ACCOUNT_EXTENDED_PROPERTIES_HISTORY")
