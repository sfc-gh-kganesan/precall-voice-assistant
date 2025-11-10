"""
JIRA Service - Business logic for JIRA ticket search operations.

This service handles:
- Searching tickets by query ID, account, case
- Finding similar/duplicate tickets
- Converting JIRA objects to Pydantic models
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from jira.exceptions import JIRAError

from app.config import settings
from app.integrations.jira.client import JiraClient, get_jira_client
from app.integrations.jira.jql_builder import JQLBuilder
from app.integrations.jira.models import (
    JiraSearchResponse,
    JiraTicket,
    SimilarTicketResult,
    SimilarTicketsResponse,
)
from app.services.base import BaseService

logger = logging.getLogger(__name__)

# Custom field IDs (matching jql_builder.py)
CUSTOM_FIELD_ACCOUNT_LOCATOR = "customfield_13335"
CUSTOM_FIELD_DEPLOYMENT = "customfield_13340"
CUSTOM_FIELD_AREA = "customfield_11401"
CUSTOM_FIELD_ERROR_MESSAGE = "customfield_13342"


class JiraService(BaseService):
    """Service for JIRA ticket search operations."""

    def __init__(self):
        super().__init__()
        self.jira_client: Optional[JiraClient] = None
        self.jql_builder = JQLBuilder()

        # Initialize JIRA client if enabled
        if settings.JIRA_ENABLED:
            try:
                self.jira_client = get_jira_client()
                logger.info("JIRA service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize JIRA client: {e}")
                raise

    def _check_enabled(self):
        """Check if JIRA integration is enabled and client is available."""
        if not settings.JIRA_ENABLED or self.jira_client is None:
            raise ValueError(
                "JIRA integration is not enabled. Set JIRA_ENABLED=true and configure credentials."
            )

    def _parse_issue_to_dict(self, issue: Any) -> Dict[str, Any]:
        """
        Convert JIRA issue object to dictionary.

        Args:
            issue: JIRA issue object

        Returns:
            Dictionary with parsed ticket data
        """
        # Parse dates
        created = datetime.fromisoformat(issue.fields.created.replace("Z", "+00:00"))
        updated = datetime.fromisoformat(issue.fields.updated.replace("Z", "+00:00"))

        # Get assignee and reporter
        assignee = None
        if hasattr(issue.fields, "assignee") and issue.fields.assignee:
            assignee = issue.fields.assignee.displayName

        reporter = None
        if hasattr(issue.fields, "reporter") and issue.fields.reporter:
            reporter = issue.fields.reporter.displayName

        # Get priority
        priority = "None"
        if hasattr(issue.fields, "priority") and issue.fields.priority:
            priority = issue.fields.priority.name

        # Get status
        status = "Unknown"
        if hasattr(issue.fields, "status") and issue.fields.status:
            status = issue.fields.status.name

        # Get custom fields
        account_locator = self.jira_client.get_custom_field_value(
            issue, CUSTOM_FIELD_ACCOUNT_LOCATOR
        )
        deployment_raw = self.jira_client.get_custom_field_value(
            issue, CUSTOM_FIELD_DEPLOYMENT
        )
        area_raw = self.jira_client.get_custom_field_value(issue, CUSTOM_FIELD_AREA)
        error_message = self.jira_client.get_custom_field_value(
            issue, CUSTOM_FIELD_ERROR_MESSAGE
        )

        # Extract values from complex custom field objects
        deployment = None
        if (
            deployment_raw
            and isinstance(deployment_raw, list)
            and len(deployment_raw) > 0
        ):
            deployment = deployment_raw[0]

        area = None
        if area_raw and hasattr(area_raw, "value"):
            area = area_raw.value

        # Get component
        component = None
        if hasattr(issue.fields, "components") and issue.fields.components:
            component = issue.fields.components[0].name

        return {
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": status,
            "priority": priority,
            "assignee": assignee,
            "reporter": reporter,
            "created": created,
            "updated": updated,
            "url": self.jira_client.build_issue_url(issue.key),
            "account_locator": account_locator,
            "deployment": deployment,
            "area": area,
            "error_message": error_message,
            "component": component,
        }

    def search_by_query_id(
        self, query_id: str, max_results: int = None
    ) -> JiraSearchResponse:
        """
        Search JIRA tickets by query ID.

        Args:
            query_id: Snowflake query ID
            max_results: Maximum results (default from settings)

        Returns:
            JiraSearchResponse with matching tickets
        """
        self._check_enabled()
        logger.info(f"Searching JIRA tickets for query_id: {query_id}")

        max_results = max_results or settings.JIRA_MAX_RESULTS
        jql = self.jql_builder.by_query_id(query_id)

        try:
            issues = self.jira_client.search_issues(jql, max_results=max_results)
            tickets = [
                JiraTicket(**self._parse_issue_to_dict(issue)) for issue in issues
            ]

            return JiraSearchResponse(
                count=len(tickets), total=len(tickets), tickets=tickets
            )
        except JIRAError as e:
            logger.error(f"JIRA search failed for query_id {query_id}: {e}")
            raise

    def search_by_account_locator(
        self,
        account_locator: str,
        status: Optional[List[str]] = None,
        max_results: int = None,
    ) -> JiraSearchResponse:
        """
        Search JIRA tickets by account locator.

        Args:
            account_locator: Account locator
            status: Optional status filter
            max_results: Maximum results (default from settings)

        Returns:
            JiraSearchResponse with matching tickets
        """
        self._check_enabled()
        logger.info(f"Searching JIRA tickets for account: {account_locator}")

        max_results = max_results or settings.JIRA_MAX_RESULTS
        jql = self.jql_builder.by_account_locator(account_locator, status=status)

        try:
            issues = self.jira_client.search_issues(jql, max_results=max_results)
            tickets = [
                JiraTicket(**self._parse_issue_to_dict(issue)) for issue in issues
            ]

            return JiraSearchResponse(
                count=len(tickets), total=len(tickets), tickets=tickets
            )
        except JIRAError as e:
            logger.error(f"JIRA search failed for account {account_locator}: {e}")
            raise

    def search_by_case_number(
        self, case_number: str, max_results: int = None
    ) -> JiraSearchResponse:
        """
        Search JIRA tickets by case number.

        Args:
            case_number: Salesforce case number
            max_results: Maximum results (default from settings)

        Returns:
            JiraSearchResponse with matching tickets
        """
        self._check_enabled()
        logger.info(f"Searching JIRA tickets for case: {case_number}")

        max_results = max_results or settings.JIRA_MAX_RESULTS
        jql = self.jql_builder.by_case_number(case_number)

        try:
            issues = self.jira_client.search_issues(jql, max_results=max_results)
            tickets = [
                JiraTicket(**self._parse_issue_to_dict(issue)) for issue in issues
            ]

            return JiraSearchResponse(
                count=len(tickets), total=len(tickets), tickets=tickets
            )
        except JIRAError as e:
            logger.error(f"JIRA search failed for case {case_number}: {e}")
            raise

    def find_similar_tickets(
        self,
        error_message: Optional[str] = None,
        component: Optional[str] = None,
        deployment: Optional[str] = None,
        area: Optional[str] = None,
        days: int = 30,
        similarity_threshold: float = 0.5,
        max_results: int = None,
    ) -> SimilarTicketsResponse:
        """
        Find similar tickets based on error message and metadata.

        Args:
            error_message: Error message to search for
            component: Component name
            deployment: Deployment name
            area: JIRA area
            days: Search last N days (default 30)
            similarity_threshold: Minimum similarity score (0-1)
            max_results: Maximum results (default from settings)

        Returns:
            SimilarTicketsResponse with matching tickets and scores
        """
        self._check_enabled()
        logger.info("Searching for similar JIRA tickets")

        max_results = max_results or settings.JIRA_MAX_RESULTS
        jql = self.jql_builder.find_similar(
            error_message=error_message,
            component=component,
            deployment=deployment,
            area=area,
            days=days,
        )

        try:
            issues = self.jira_client.search_issues(jql, max_results=max_results)

            # Calculate similarity scores and build results
            results = []
            for issue in issues:
                ticket_dict = self._parse_issue_to_dict(issue)
                score, reasons = self._calculate_similarity(
                    ticket_dict,
                    error_message=error_message,
                    component=component,
                    deployment=deployment,
                    area=area,
                )

                if score >= similarity_threshold:
                    results.append(
                        SimilarTicketResult(
                            ticket=JiraTicket(**ticket_dict),
                            similarity_score=score,
                            match_reasons=reasons,
                        )
                    )

            # Sort by similarity score descending
            results.sort(key=lambda x: x.similarity_score, reverse=True)

            return SimilarTicketsResponse(count=len(results), tickets=results)
        except JIRAError as e:
            logger.error(f"JIRA similar ticket search failed: {e}")
            raise

    def _calculate_similarity(
        self,
        ticket: Dict[str, Any],
        error_message: Optional[str] = None,
        component: Optional[str] = None,
        deployment: Optional[str] = None,
        area: Optional[str] = None,
    ) -> tuple[float, List[str]]:
        """
        Calculate similarity score between search criteria and ticket.

        Args:
            ticket: Ticket dictionary
            error_message: Expected error message
            component: Expected component
            deployment: Expected deployment
            area: Expected area

        Returns:
            Tuple of (score, match_reasons)
        """
        score = 0.0
        reasons = []
        total_criteria = 0

        # Error message match (40% weight)
        if error_message and ticket.get("error_message"):
            total_criteria += 1
            ticket_error = ticket["error_message"].lower()
            search_error = error_message.lower()
            if search_error in ticket_error or ticket_error in search_error:
                score += 0.4
                reasons.append("Similar error message")

        # Component match (20% weight)
        if component:
            total_criteria += 1
            if ticket.get("component") == component:
                score += 0.2
                reasons.append(f"Same component: {component}")

        # Deployment match (20% weight)
        if deployment:
            total_criteria += 1
            if (
                ticket.get("deployment")
                and deployment.lower() in str(ticket["deployment"]).lower()
            ):
                score += 0.2
                reasons.append(f"Same deployment: {deployment}")

        # Area match (20% weight)
        if area:
            total_criteria += 1
            if ticket.get("area") == area:
                score += 0.2
                reasons.append(f"Same area: {area}")

        # Normalize score if not all criteria provided
        if total_criteria > 0:
            # Adjust score based on how many criteria were actually used
            max_possible = total_criteria / 5  # 5 total possible criteria
            score = score / max_possible if max_possible > 0 else score

        return (min(score, 1.0), reasons)

    def get_ticket(self, ticket_key: str) -> JiraTicket:
        """
        Get a single JIRA ticket by key.

        Args:
            ticket_key: JIRA ticket key (e.g., "SNOW-12345")

        Returns:
            JiraTicket object
        """
        self._check_enabled()
        logger.info(f"Fetching JIRA ticket: {ticket_key}")

        try:
            issue = self.jira_client.get_issue(ticket_key)
            ticket_dict = self._parse_issue_to_dict(issue)
            return JiraTicket(**ticket_dict)
        except JIRAError as e:
            logger.error(f"Failed to fetch JIRA ticket {ticket_key}: {e}")
            raise
