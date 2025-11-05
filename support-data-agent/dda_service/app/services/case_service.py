"""
Case Service - Business logic for case-related operations.

This service handles all case-related operations including:
- Case metadata retrieval
- Case-to-queries mapping
- Case search and filtering
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.queries.case_queries import CaseQueries
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class CaseService(BaseService):
    """Service for case operations."""

    def __init__(self):
        super().__init__()
        self.case_queries = CaseQueries()

    def get_case_metadata(self, case_number: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific case.

        Args:
            case_number: Salesforce case number (e.g., "01087579")

        Returns:
            Dictionary containing case metadata, or None if case not found
        """
        logger.info(f"Getting metadata for case: {case_number}")

        params = {"case_number": case_number}
        df = self.execute_query(
            self.case_queries.get_case_metadata, params, use_cache=True
        )

        if df.empty:
            logger.warning(f"Case not found: {case_number}")
            return None

        return df.iloc[0].to_dict()

    def get_case_queries(self, case_number: str) -> List[Dict[str, Any]]:
        """
        Get all queries associated with a case.

        Args:
            case_number: Salesforce case number

        Returns:
            List of query dictionaries with metadata
        """
        logger.info(f"Getting queries for case: {case_number}")

        params = {"case_number": case_number}
        df = self.execute_query(
            self.case_queries.get_case_queries, params, use_cache=True
        )

        if df.empty:
            logger.info(f"No queries found for case: {case_number}")
            return []

        return df.to_dict(orient="records")

    def get_case_query_count(self, case_number: str) -> int:
        """
        Get count of queries associated with a case.

        Args:
            case_number: Salesforce case number

        Returns:
            Number of queries linked to the case
        """
        logger.info(f"Getting query count for case: {case_number}")

        params = {"case_number": case_number}
        df = self.execute_query(
            self.case_queries.get_case_query_count, params, use_cache=True
        )

        if df.empty:
            return 0

        return int(df.iloc[0]["QUERY_COUNT"])

    def search_cases(
        self,
        status: Optional[str] = None,
        is_closed: Optional[bool] = None,
        functional_area: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search cases by various criteria.

        Args:
            status: Case status (e.g., "Open", "Closed", "Escalated")
            is_closed: Whether case is closed
            functional_area: Functional area (e.g., "Performance", "Security")
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            limit: Maximum number of results (default 100, max 1000)

        Returns:
            List of case dictionaries matching criteria
        """
        logger.info(
            f"Searching cases: status={status}, is_closed={is_closed}, "
            f"functional_area={functional_area}, limit={limit}"
        )

        # Enforce reasonable limit
        if limit > 1000:
            limit = 1000

        params = {
            "status": status,
            "is_closed": is_closed,
            "functional_area": functional_area,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        }

        df = self.execute_query(self.case_queries.search_cases, params, use_cache=True)

        if df.empty:
            logger.info("No cases found matching criteria")
            return []

        return df.to_dict(orient="records")
