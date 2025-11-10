"""
TSW (Troubleshooting Wizard) Service - Business logic for TSW diagnostic operations.

This service handles all TSW-related operations including:
- UDF Analysis
- Query Compilation
- Iceberg Tables
- Query Locks
- Incident Errors
- User Authentication (SAML/OAUTH)
- RBAC Analysis
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np

from app.queries.tsw.auth_queries import AuthQueries
from app.queries.tsw.compilation_queries import CompilationQueries
from app.queries.tsw.iceberg_queries import IcebergQueries
from app.queries.tsw.incident_queries import IncidentQueries
from app.queries.tsw.locks_queries import LocksQueries
from app.queries.tsw.rbac_queries import RbacQueries
from app.queries.tsw.udf_queries import UdfQueries
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class TswService(BaseService):
    """Service for TSW diagnostic operations."""

    def __init__(self):
        super().__init__()
        self.udf_queries = UdfQueries()
        self.compilation_queries = CompilationQueries()
        self.incident_queries = IncidentQueries()
        self.iceberg_queries = IcebergQueries()
        self.locks_queries = LocksQueries()
        self.auth_queries = AuthQueries()
        self.rbac_queries = RbacQueries()

    # =========================================================================
    # 1. UDF Analysis
    # =========================================================================

    def analyze_udf(self, query_id: str) -> Dict[str, Any]:
        """
        Analyze UDF usage for a query.

        Args:
            query_id: Query ID to analyze

        Returns:
            Dictionary containing:
            - query_metadata: Basic query information
            - udf_json: UDF analysis results from stored procedure
            - table_objects: Tables accessed by the query
        """
        logger.info(f"Analyzing UDF for query: {query_id}")

        result = {}

        # Get query metadata
        params = {"queryid": query_id}
        metadata_df = self.execute_query(
            self.udf_queries.get_queryid_metadata, params, use_cache=True
        )
        if not metadata_df.empty:
            metadata_df = metadata_df.replace({np.nan: None})
            result["query_metadata"] = metadata_df.iloc[0].to_dict()

        # Get UDF JSON from stored procedure
        try:
            udf_json_df = self.execute_query(
                self.udf_queries.get_udf_json, params, use_cache=False
            )
            if not udf_json_df.empty:
                udf_json_df = udf_json_df.replace({np.nan: None})
                result["udf_analysis"] = udf_json_df.to_dict(orient="records")
        except Exception as e:
            logger.warning(f"UDF stored procedure failed: {e}")
            result["udf_analysis"] = None

        # Get table objects
        table_objects_df = self.execute_query(
            self.udf_queries.get_table_objects, params, use_cache=True
        )
        if not table_objects_df.empty:
            table_objects_df = table_objects_df.replace({np.nan: None})
            result["table_objects"] = table_objects_df.to_dict(orient="records")

        return result

    # =========================================================================
    # 2. Query Compilation Analysis
    # =========================================================================

    def analyze_compilation(self, case_number: str) -> Dict[str, Any]:
        """
        Analyze query compilation issues for a case.

        Args:
            case_number: Case number to analyze

        Returns:
            Dictionary containing:
            - queries_with_compilation_issues: Queries with high compilation time
            - query_metadata: Metadata for all queries in the case
            - package_data: Pre-computed data if available
        """
        logger.info(f"Analyzing compilation for case: {case_number}")

        result = {}

        # Get query metadata for the case
        params = {"casenumber": case_number}
        metadata_df = self.execute_query(
            self.compilation_queries.get_query_comp_metadata, params, use_cache=True
        )

        if metadata_df.empty:
            logger.warning(f"No queries found for case: {case_number}")
            return result

        result["query_metadata"] = metadata_df.to_dict(orient="records")

        # For each query, check compilation time
        queries_with_issues = []
        for _, row in metadata_df.iterrows():
            query_id = row["QUERYID"]
            row["ACCOUNT_ID"]
            row["DEPLOYMENT"]

            # Get duration values
            dur_params = {"queryid": query_id}
            dur_df = self.execute_query(
                self.compilation_queries.get_querycomp_dur_vals,
                dur_params,
                use_cache=True,
            )

            if not dur_df.empty:
                dur_data = dur_df.iloc[0].to_dict()
                dur_data["query_id"] = query_id
                queries_with_issues.append(dur_data)

            # Check for package data
            package_params = {"casenumber": case_number, "queryid": query_id}
            package_df = self.execute_query(
                self.compilation_queries.get_querycomp_json_from_tsw_compilation_package,
                package_params,
                use_cache=True,
            )
            if not package_df.empty:
                if "package_data" not in result:
                    result["package_data"] = []
                result["package_data"].append(
                    {"query_id": query_id, "data": package_df.iloc[0].to_dict()}
                )

        result["queries_with_issues"] = queries_with_issues
        return result

    # =========================================================================
    # 3. Iceberg Table Diagnostics
    # =========================================================================

    def analyze_iceberg(
        self, query_id: str, case_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze Iceberg table issues for a query.

        Args:
            query_id: Query ID to analyze
            case_number: Optional case number for package data lookup

        Returns:
            Dictionary containing:
            - table_name: Iceberg table name
            - package_data: Pre-computed data if available
        """
        logger.info(f"Analyzing Iceberg table for query: {query_id}")

        result = {}

        # Get Iceberg table name
        params = {"queryid": query_id}
        table_df = self.execute_query(
            self.iceberg_queries.get_iceberg_table_name, params, use_cache=True
        )

        if not table_df.empty:
            table_name = table_df.iloc[0].iloc[0]  # First column of first row
            result["table_name"] = table_name

            # Check for package data if case number provided
            if case_number and table_name:
                package_params = {
                    "casenumber": case_number,
                    "queryid": query_id,
                    "icebergtablename": table_name,
                }
                package_df = self.execute_query(
                    self.iceberg_queries.get_iceberg_json_from_tsw_iceberg_package,
                    package_params,
                    use_cache=True,
                )
                if not package_df.empty:
                    result["package_data"] = package_df.iloc[0].to_dict()

        return result

    # =========================================================================
    # 4. Query Locks Analysis
    # =========================================================================

    def analyze_locks(
        self,
        query_id: str,
        deployment: str,
        account_id: int,
        case_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze query lock issues.

        Args:
            query_id: Query ID to analyze
            deployment: Snowflake deployment
            account_id: Account ID
            case_number: Optional case number for package data lookup

        Returns:
            Dictionary containing:
            - locking_queries: Queries that were blocking this query
            - package_data: Pre-computed data if available
        """
        logger.info(f"Analyzing locks for query: {query_id}")

        result = {}

        # Get locking query metadata from SNOWHOUSE_IMPORT
        lock_query = self.locks_queries.get_locking_queries_md(deployment)
        params = {"queryid": query_id, "account_id": account_id}

        try:
            lock_df = self.execute_query(lock_query, params, use_cache=True)
            if not lock_df.empty:
                result["locking_queries"] = lock_df.to_dict(orient="records")
        except Exception as e:
            logger.warning(f"Could not fetch locking queries: {e}")
            result["locking_queries"] = []

        # Check for package data
        if case_number:
            package_params = {"casenumber": case_number, "queryid": query_id}
            package_df = self.execute_query(
                self.locks_queries.get_querylock_json_from_tsw_locks_package,
                package_params,
                use_cache=True,
            )
            if not package_df.empty:
                result["package_data"] = package_df.iloc[0].to_dict()

        return result

    # =========================================================================
    # 5. Incident Errors Analysis
    # =========================================================================

    def analyze_incidents(self, case_number: str) -> Dict[str, Any]:
        """
        Analyze incident errors for a case.

        Args:
            case_number: Case number to analyze

        Returns:
            Dictionary containing:
            - query_ids: List of query IDs with incident errors
            - package_data: Pre-computed data for each query if available
        """
        logger.info(f"Analyzing incidents for case: {case_number}")

        result = {}

        # Get queries with incidents
        params = {"case_number": case_number}
        incident_df = self.execute_query(
            self.incident_queries.get_query_incident_errors_cases,
            params,
            use_cache=True,
        )

        if incident_df.empty:
            logger.info(f"No incident errors found for case: {case_number}")
            return {"query_ids": [], "package_data": []}

        query_ids = incident_df["QUERYID"].tolist()
        result["query_ids"] = query_ids

        # Check for package data for each query
        package_data = []
        for query_id in query_ids:
            package_params = {"case_number": case_number, "queryid": query_id}
            package_df = self.execute_query(
                self.incident_queries.get_queryincidenterrors_json_from_tsw_errors_package,
                package_params,
                use_cache=True,
            )
            if not package_df.empty:
                package_data.append(
                    {"query_id": query_id, "data": package_df.iloc[0].to_dict()}
                )

        result["package_data"] = package_data
        return result

    # =========================================================================
    # 6. User Authentication (SAML/OAUTH) Analysis
    # =========================================================================

    def analyze_auth(
        self,
        deployment: str,
        account_id: int,
        case_number: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Analyze user authentication issues (SAML/OAUTH).

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            case_number: Optional case number for package data lookup
            start_time: Optional start time for log queries
            end_time: Optional end time for log queries

        Returns:
            Dictionary containing:
            - saml_integrations: SAML integration details
            - oauth_integrations: OAUTH integration details
            - saml_logs: SAML authentication logs (if time range provided)
            - oauth_logs: OAUTH authentication logs (if time range provided)
            - package_data: Pre-computed data if available
        """
        logger.info(
            f"Analyzing auth for deployment: {deployment}, account: {account_id}"
        )

        result = {}

        # Get SAML integrations
        saml_params = {"account_id": account_id, "deployment": deployment}
        saml_df = self.execute_query(
            self.auth_queries.get_saml_list, saml_params, use_cache=True
        )
        if not saml_df.empty:
            saml_df = saml_df.replace({np.nan: None})
            result["saml_integrations"] = saml_df.to_dict(orient="records")

        # Get OAUTH integrations
        oauth_query = self.auth_queries.get_oauth_list(deployment)
        oauth_params = {"account_id": account_id}
        try:
            oauth_df = self.execute_query(oauth_query, oauth_params, use_cache=True)
            if not oauth_df.empty:
                oauth_df = oauth_df.replace({np.nan: None})
                result["oauth_integrations"] = oauth_df.to_dict(orient="records")
        except Exception as e:
            logger.warning(f"Could not fetch OAUTH integrations: {e}")
            result["oauth_integrations"] = []

        # Get logs if time range provided
        if start_time and end_time:
            log_params = {
                "account_id": account_id,
                "start_time": start_time,
                "end_time": end_time,
            }

            # SAML logs
            saml_log_query = self.auth_queries.get_saml_logs(deployment)
            try:
                saml_log_df = self.execute_query(
                    saml_log_query, log_params, use_cache=False
                )
                if not saml_log_df.empty:
                    saml_log_df = saml_log_df.replace({np.nan: None})
                    result["saml_logs"] = saml_log_df.to_dict(orient="records")
            except Exception as e:
                logger.warning(f"Could not fetch SAML logs: {e}")

            # OAUTH logs
            oauth_log_query = self.auth_queries.get_oauth_logs(deployment)
            try:
                oauth_log_df = self.execute_query(
                    oauth_log_query, log_params, use_cache=False
                )
                if not oauth_log_df.empty:
                    oauth_log_df = oauth_log_df.replace({np.nan: None})
                    result["oauth_logs"] = oauth_log_df.to_dict(orient="records")
            except Exception as e:
                logger.warning(f"Could not fetch OAUTH logs: {e}")

        # Check for package data
        if case_number:
            package_params = {
                "case_number": case_number,
                "deployment": deployment,
                "account_id": account_id,
            }
            package_df = self.execute_query(
                self.auth_queries.get_userauth_json_from_tsw_userauth_package,
                package_params,
                use_cache=True,
            )
            if not package_df.empty:
                package_df = package_df.replace({np.nan: None})
                result["package_data"] = package_df.iloc[0].to_dict()

        return result

    # =========================================================================
    # 7. RBAC Analysis
    # =========================================================================

    def analyze_rbac(
        self, query_id: str, deployment: str, account_id: int
    ) -> Dict[str, Any]:
        """
        Analyze RBAC (Role-Based Access Control) issues for a query.

        Args:
            query_id: Query ID to analyze
            deployment: Snowflake deployment
            account_id: Account ID

        Returns:
            Dictionary containing:
            - query_details: Query metadata including error details
            - candidate_securables: Securables that might be causing the issue
            - user_data: User information (if available)
            - role_data: Role information (if available)
        """
        logger.info(f"Analyzing RBAC for query: {query_id}")

        result = {}

        # Get query details
        params = {"queryid": query_id}
        details_df = self.execute_query(
            self.rbac_queries.get_rbac_query_details, params, use_cache=True
        )

        if details_df.empty:
            logger.warning(f"No query details found for: {query_id}")
            return result

        query_details = details_df.iloc[0].to_dict()
        result["query_details"] = query_details

        # Get candidate securables from stored procedure
        try:
            securables_df = self.execute_query(
                self.rbac_queries.get_rbac_candidate_securables,
                params,
                use_cache=False,
            )
            if not securables_df.empty:
                result["candidate_securables"] = securables_df.to_dict(orient="records")
        except Exception as e:
            logger.warning(f"Could not fetch candidate securables: {e}")
            result["candidate_securables"] = []

        # Get user data if user_name is available
        if query_details.get("user_name"):
            user_query = self.rbac_queries.get_rbac_user_data(deployment)
            user_params = {
                "user_name": query_details["user_name"],
                "account_id": account_id,
                "client_send_time": query_details.get("client_send_time"),
            }
            try:
                user_df = self.execute_query(user_query, user_params, use_cache=True)
                if not user_df.empty:
                    result["user_data"] = user_df.iloc[0].to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch user data: {e}")

        # Get role data if role_name is available
        if query_details.get("role_name"):
            role_query = self.rbac_queries.get_rbac_role_data(deployment)
            role_params = {
                "role_name": query_details["role_name"],
                "account_id": account_id,
                "client_send_time": query_details.get("client_send_time"),
            }
            try:
                role_df = self.execute_query(role_query, role_params, use_cache=True)
                if not role_df.empty:
                    result["role_data"] = role_df.iloc[0].to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch role data: {e}")

        return result
