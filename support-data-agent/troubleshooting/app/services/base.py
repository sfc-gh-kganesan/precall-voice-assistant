"""
Base service class with common query execution and caching logic.
All service classes inherit from this base.
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd

from app.core.cache import get_cache
from app.core.database import get_connection_manager
from app.core.table_mappings import get_table_mappings

logger = logging.getLogger(__name__)


class BaseService:
    """
    Base class for all service layer classes.
    Provides query execution with automatic caching support.
    """

    def __init__(self):
        """Initialize service with database and cache managers"""
        self.db = get_connection_manager()
        self.cache = get_cache()
        # Load table/view mappings for the current environment
        self._table_mappings = get_table_mappings()

    def _merge_params_with_table_mappings(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Merge user-provided parameters with default table/view mappings.

        Args:
            params: User-provided query parameters

        Returns:
            Dict with both table mappings and user parameters
        """
        # Start with table mappings as the base
        merged_params = self._table_mappings.copy()

        # Merge in user-provided parameters (they override table mappings if there's overlap)
        if params:
            merged_params.update(params)

        return merged_params

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        connection_type: str = "READ",
    ) -> pd.DataFrame:
        """
        Execute a query with optional caching.

        Args:
            query: SQL query string
            params: Query parameters
            use_cache: Whether to use cache (default: True)
            connection_type: "READ", "WRITE", or "QUERY_CATALOG"

        Returns:
            DataFrame: Query results
        """
        # Merge user params with table/view mappings
        merged_params = self._merge_params_with_table_mappings(params)

        # Check cache first if enabled
        if use_cache:
            cached_result = self.cache.get(query, merged_params)
            if cached_result is not None:
                logger.debug("Returning cached result")
                return cached_result

        # Execute query
        result = self.db.execute_query(query, merged_params, connection_type)

        # Cache result if caching is enabled
        if use_cache:
            self.cache.set(query, merged_params, result)

        return result

    def execute_query_async(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        connection_type: str = "READ",
    ) -> str:
        """
        Execute query asynchronously and return query ID.

        Args:
            query: SQL query string
            params: Query parameters
            connection_type: "READ" or "WRITE"

        Returns:
            str: Snowflake query ID
        """
        # Merge user params with table/view mappings
        merged_params = self._merge_params_with_table_mappings(params)
        return self.db.execute_query_async(query, merged_params, connection_type)

    def get_async_results(self, query_id: str) -> pd.DataFrame:
        """
        Get results from an async query.

        Args:
            query_id: Snowflake query ID

        Returns:
            DataFrame: Query results
        """
        return self.db.get_async_results(query_id)
