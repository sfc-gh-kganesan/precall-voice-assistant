"""
Account Service - Business logic for account operations.

This service handles all account-related operations including search, metadata retrieval,
warehouse listings, case associations, query history, and environment information.
"""

from typing import Dict, Optional, Any, List
import logging

from app.services.base import BaseService
from app.queries.account_queries import AccountViewQueries

logger = logging.getLogger(__name__)


class AccountService(BaseService):
    """Service for account operations."""

    def __init__(self):
        super().__init__()
        self.queries = AccountViewQueries()

    def search_accounts(
        self, search_query: str, deployment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for accounts by partial match on locator, alias, or account ID.

        Results are ranked with exact matches first, then partial matches.

        Args:
            search_query: Search term (account locator, alias, or ID)
            deployment: Optional deployment filter

        Returns:
            List of matching accounts with deployment, alias, locator, account_id
        """
        logger.info(f"Searching accounts with query: {search_query}")

        # Prepare wildcard pattern for ILIKE queries
        wildcard_pattern = f"%{search_query}%"

        params = {
            "search_query_value": search_query,
            "search_query_wildcard_pattern": wildcard_pattern,
        }

        result_df = self.execute_query(
            self.queries.account_search_query, params, use_cache=True
        )

        if result_df.empty:
            logger.info(f"No accounts found for query: {search_query}")
            return []

        # Convert to list of dicts
        accounts = result_df.to_dict(orient="records")
        logger.info(f"Found {len(accounts)} accounts")

        return accounts

    def get_account_metadata(
        self, deployment: str, acc_locator: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive account metadata.

        Returns detailed information including:
        - Basic info (name, alias, deployment, account_id)
        - Service level, account status/type
        - Version/release groups
        - Load balancer type
        - Cloud provider and region information

        Args:
            deployment: Snowflake deployment
            acc_locator: Account locator (name)

        Returns:
            Dictionary with account metadata, or None if not found
        """
        logger.info(f"Fetching metadata for account: {acc_locator} in {deployment}")

        params = {
            "acc_locator": acc_locator,
            "dda_snwflk_deployment": deployment,
        }

        result_df = self.execute_query(
            self.queries.account_metadata, params, use_cache=True
        )

        if result_df.empty:
            logger.warning(
                f"No metadata found for account: {acc_locator} in {deployment}"
            )
            return None

        # Convert first row to dictionary
        metadata = result_df.iloc[0].to_dict()

        # Convert timestamps to ISO format if present
        for date_field in ["DELETED_ON", "CREATED_ON"]:
            if date_field in metadata and metadata[date_field] is not None:
                metadata[date_field] = metadata[date_field].isoformat()

        return metadata

    def get_release_history(
        self, deployment: str, account_id: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get release version history for an account.

        Args:
            deployment: Snowflake deployment
            account_id: Account ID
            limit: Maximum number of releases to return

        Returns:
            List of releases with version and timestamp
        """
        logger.info(f"Fetching release history for account_id: {account_id}")

        params = {
            "account_id": account_id,
            "dda_snwflk_deployment": deployment,
        }

        result_df = self.execute_query(
            self.queries.release_version, params, use_cache=True
        )

        if result_df.empty:
            logger.info(f"No release history found for account_id: {account_id}")
            return []

        # Limit results
        result_df = result_df.head(limit)

        # Convert timestamps
        releases = result_df.to_dict(orient="records")
        for release in releases:
            if "RELEASE_TIME" in release and release["RELEASE_TIME"] is not None:
                release["RELEASE_TIME"] = release["RELEASE_TIME"].isoformat()

        logger.info(f"Found {len(releases)} releases")
        return releases

    def get_account_warehouses(
        self, deployment: str, account_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of warehouses for an account.

        Returns warehouse information including size, type, and load data availability.

        Args:
            deployment: Snowflake deployment
            account_id: Account ID

        Returns:
            List of warehouses with metadata
        """
        logger.info(f"Fetching warehouses for account_id: {account_id}")

        params = {
            "account_id": account_id,
            "dda_snwflk_deployment": deployment,
        }

        result_df = self.execute_query(
            self.queries.get_account_warehouses, params, use_cache=True
        )

        if result_df.empty:
            logger.info(f"No warehouses found for account_id: {account_id}")
            return []

        # Convert timestamps
        warehouses = result_df.to_dict(orient="records")
        for wh in warehouses:
            for date_field in [
                "LAST_PROVISIONED_ON",
                "UPDATED_ON",
                "CREATED_ON",
                "DELETED_ON",
                "START_TIME",
                "END_TIME",
            ]:
                if date_field in wh and wh[date_field] is not None:
                    wh[date_field] = wh[date_field].isoformat()

        logger.info(f"Found {len(warehouses)} warehouses")
        return warehouses

    def get_open_cases(
        self, deployment: str, acc_locator: str, acc_alias: str
    ) -> List[Dict[str, Any]]:
        """
        Get open Salesforce cases for an account.

        Args:
            deployment: Snowflake deployment
            acc_locator: Account locator
            acc_alias: Account alias

        Returns:
            List of open cases with status, category, and subject
        """
        logger.info(f"Fetching open cases for account: {acc_locator}")

        params = {
            "acc_locator": acc_locator,
            "acc_alias": acc_alias,
        }

        result_df = self.execute_query(
            self.queries.get_open_cases_for_account, params, use_cache=True
        )

        if result_df.empty:
            logger.info(f"No open cases found for account: {acc_locator}")
            return []

        # Convert timestamps
        cases = result_df.to_dict(orient="records")
        for case in cases:
            if "CREATED_DATE" in case and case["CREATED_DATE"] is not None:
                case["CREATED_DATE"] = case["CREATED_DATE"].isoformat()

        logger.info(f"Found {len(cases)} open cases")
        return cases

    def get_account_queries(
        self, deployment: str, acc_locator: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get queries executed on this account.

        Args:
            deployment: Snowflake deployment
            acc_locator: Account locator
            limit: Maximum number of queries to return

        Returns:
            List of queries with query_id, case_number, timestamp, and SQL hash
        """
        logger.info(f"Fetching queries for account: {acc_locator}")

        params = {
            "acc_locator": acc_locator,
            "dda_snwflk_deployment": deployment,
        }

        result_df = self.execute_query(
            self.queries.dda_quuid_with_same_account, params, use_cache=True
        )

        if result_df.empty:
            logger.info(f"No queries found for account: {acc_locator}")
            return []

        # Limit results
        result_df = result_df.head(limit)

        # Convert timestamps
        queries = result_df.to_dict(orient="records")
        for query in queries:
            if "CLIENT_SEND_TIME" in query and query["CLIENT_SEND_TIME"] is not None:
                query["CLIENT_SEND_TIME"] = query["CLIENT_SEND_TIME"].isoformat()

        logger.info(f"Found {len(queries)} queries")
        return queries

    def get_account_environment(
        self, deployment: str, account_id: int
    ) -> Optional[str]:
        """
        Get account environment type (prod/dev/test/etc).

        Args:
            deployment: Snowflake deployment
            account_id: Account ID

        Returns:
            Environment string, or None if not found
        """
        logger.info(f"Fetching environment for account_id: {account_id}")

        params = {
            "account_id": account_id,
            "dda_snwflk_deployment": deployment,
        }

        result_df = self.execute_query(
            self.queries.get_account_environment, params, use_cache=True
        )

        if result_df.empty:
            logger.info(f"No environment found for account_id: {account_id}")
            return None

        environment = result_df.iloc[0]["ENVIRONMENT"]
        return environment
