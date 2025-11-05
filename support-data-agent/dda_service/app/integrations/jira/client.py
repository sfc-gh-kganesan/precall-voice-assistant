"""
JIRA client wrapper for API interactions.

Provides a singleton client instance with connection pooling and error handling.
"""

import logging
from functools import lru_cache
from typing import Any, List, Optional

from jira import JIRA
from jira.exceptions import JIRAError

from app.config import settings

logger = logging.getLogger(__name__)


class JiraClient:
    """
    Wrapper around jira-python library with error handling and convenience methods.
    """

    def __init__(self, account: str, user: str, api_token: str):
        """
        Initialize JIRA client with authentication.

        Args:
            account: JIRA account name (e.g., "snowflakecomputing")
            user: JIRA user email
            api_token: JIRA API token

        Raises:
            JIRAError: If authentication fails
        """
        self.account = account
        self.jira_url = f"https://{account}.atlassian.net"

        try:
            self._client = JIRA(
                server=self.jira_url,
                basic_auth=(user, api_token),
            )
            logger.info(f"Successfully connected to JIRA at {self.jira_url}")
        except JIRAError as e:
            logger.error(f"Failed to connect to JIRA: {e}")
            raise

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
        expand: Optional[str] = None,
    ) -> List[Any]:
        """
        Execute JQL search and return matching issues.

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return (default 50)
            fields: List of fields to include in response (default: all)
            expand: Additional data to expand (e.g., "changelog")

        Returns:
            List of JIRA issue objects

        Raises:
            JIRAError: If search fails
        """
        try:
            logger.debug(f"Executing JQL: {jql}")
            issues = self._client.search_issues(
                jql_str=jql,
                maxResults=max_results,
                fields=fields,
                expand=expand,
            )
            logger.info(f"Found {len(issues)} issues")
            return issues
        except JIRAError as e:
            logger.error(f"JQL search failed: {e}")
            raise

    def get_issue(
        self,
        issue_key: str,
        fields: Optional[List[str]] = None,
        expand: Optional[str] = None,
    ) -> Any:
        """
        Get a single issue by key.

        Args:
            issue_key: JIRA issue key (e.g., "SNOW-12345")
            fields: List of fields to include
            expand: Additional data to expand

        Returns:
            JIRA issue object

        Raises:
            JIRAError: If issue not found or fetch fails
        """
        try:
            logger.debug(f"Fetching issue: {issue_key}")
            issue = self._client.issue(issue_key, fields=fields, expand=expand)
            return issue
        except JIRAError as e:
            logger.error(f"Failed to fetch issue {issue_key}: {e}")
            raise

    def get_custom_field_value(self, issue: Any, field_id: str) -> Optional[Any]:
        """
        Extract custom field value from issue.

        Args:
            issue: JIRA issue object
            field_id: Custom field ID (e.g., "customfield_13335")

        Returns:
            Custom field value or None if not found
        """
        try:
            return getattr(issue.fields, field_id, None)
        except AttributeError:
            return None

    def build_issue_url(self, issue_key: str) -> str:
        """
        Build full URL to JIRA issue.

        Args:
            issue_key: JIRA issue key

        Returns:
            Full URL to issue
        """
        return f"{self.jira_url}/browse/{issue_key}"

    def test_connection(self) -> bool:
        """
        Test JIRA connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._client.myself()
            return True
        except JIRAError:
            return False


@lru_cache(maxsize=1)
def get_jira_client() -> Optional[JiraClient]:
    """
    Get singleton JIRA client instance.

    Returns:
        JiraClient instance if JIRA is enabled and configured, None otherwise

    Raises:
        ValueError: If JIRA is enabled but not properly configured
    """
    if not settings.JIRA_ENABLED:
        logger.debug("JIRA integration is disabled")
        return None

    if not settings.JIRA_USER or not settings.JIRA_API_TOKEN:
        raise ValueError(
            "JIRA is enabled but JIRA_USER or JIRA_API_TOKEN not configured"
        )

    try:
        client = JiraClient(
            account=settings.JIRA_ACCOUNT,
            user=settings.JIRA_USER,
            api_token=settings.JIRA_API_TOKEN,
        )
        return client
    except JIRAError as e:
        logger.error(f"Failed to initialize JIRA client: {e}")
        raise
