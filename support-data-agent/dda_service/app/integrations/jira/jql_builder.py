"""
JQL (JIRA Query Language) query builder.

Provides helper functions to construct JQL queries for various search scenarios.
"""

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Custom field IDs used in Snowflake's JIRA
CUSTOM_FIELD_ACCOUNT_LOCATOR = "customfield_13335"
CUSTOM_FIELD_DEPLOYMENT = "customfield_13340"
CUSTOM_FIELD_AREA = "customfield_11401"
CUSTOM_FIELD_ERROR_MESSAGE = "customfield_13342"
CUSTOM_FIELD_TYPE_OF_ISSUE = "customfield_12975"


class JQLBuilder:
    """
    Builder class for constructing JQL queries.
    """

    @staticmethod
    def _escape_jql_value(value: str) -> str:
        """
        Escape special characters in JQL values.

        Args:
            value: String value to escape

        Returns:
            Escaped string safe for JQL
        """
        # Wrap in quotes and escape internal quotes
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'

    @staticmethod
    def by_query_id(query_id: str, project: str = "SNOW") -> str:
        """
        Build JQL to search for query ID in description or summary.

        Args:
            query_id: Snowflake query ID
            project: JIRA project (default: "SNOW")

        Returns:
            JQL query string
        """
        escaped_id = JQLBuilder._escape_jql_value(query_id)
        jql = (
            f'project = "{project}" '
            f"AND (description ~ {escaped_id} OR summary ~ {escaped_id})"
        )
        logger.debug(f"Built JQL for query_id: {jql}")
        return jql

    @staticmethod
    def by_account_locator(
        account_locator: str,
        project: str = "SNOW",
        status: Optional[List[str]] = None,
    ) -> str:
        """
        Build JQL to search by account locator custom field.

        Args:
            account_locator: Account locator (e.g., "ABC12345")
            project: JIRA project (default: "SNOW")
            status: Optional list of statuses to filter (e.g., ["Open", "In Progress"])

        Returns:
            JQL query string
        """
        escaped_account = JQLBuilder._escape_jql_value(account_locator)
        jql = f'project = "{project}" AND {CUSTOM_FIELD_ACCOUNT_LOCATOR} ~ {escaped_account}'

        if status:
            status_list = ", ".join([JQLBuilder._escape_jql_value(s) for s in status])
            jql += f" AND status IN ({status_list})"

        logger.debug(f"Built JQL for account_locator: {jql}")
        return jql

    @staticmethod
    def by_case_number(case_number: str, project: str = "SNOW") -> str:
        """
        Build JQL to search for case number references.

        Searches for case number in summary, description, and comments.

        Args:
            case_number: Salesforce case number (e.g., "01087579")
            project: JIRA project (default: "SNOW")

        Returns:
            JQL query string
        """
        escaped_case = JQLBuilder._escape_jql_value(case_number)
        jql = (
            f'project = "{project}" '
            f"AND (summary ~ {escaped_case} "
            f"OR description ~ {escaped_case} "
            f"OR comment ~ {escaped_case})"
        )
        logger.debug(f"Built JQL for case_number: {jql}")
        return jql

    @staticmethod
    def find_similar(
        error_message: Optional[str] = None,
        component: Optional[str] = None,
        deployment: Optional[str] = None,
        area: Optional[str] = None,
        days: int = 30,
        project: str = "SNOW",
    ) -> str:
        """
        Build JQL to find similar tickets based on error message and metadata.

        Args:
            error_message: Error message to search for
            component: Component name
            deployment: Deployment name
            area: JIRA area
            days: Search tickets created in last N days (default: 30)
            project: JIRA project (default: "SNOW")

        Returns:
            JQL query string
        """
        clauses = [f'project = "{project}"']

        if error_message:
            # Truncate long error messages for search
            truncated_error = error_message[:100]
            escaped_error = JQLBuilder._escape_jql_value(truncated_error)
            # Search in error message custom field, summary, and description
            clauses.append(
                f"({CUSTOM_FIELD_ERROR_MESSAGE} ~ {escaped_error} "
                f"OR summary ~ {escaped_error} "
                f"OR description ~ {escaped_error})"
            )

        if component:
            escaped_component = JQLBuilder._escape_jql_value(component)
            # Search in component field, summary, and description
            clauses.append(
                f"(component ~ {escaped_component} "
                f"OR summary ~ {escaped_component} "
                f"OR description ~ {escaped_component})"
            )

        if deployment:
            escaped_deployment = JQLBuilder._escape_jql_value(deployment)
            clauses.append(f"{CUSTOM_FIELD_DEPLOYMENT} ~ {escaped_deployment}")

        if area:
            escaped_area = JQLBuilder._escape_jql_value(area)
            # Search in area custom field, summary, and description
            clauses.append(
                f"({CUSTOM_FIELD_AREA} ~ {escaped_area} "
                f"OR summary ~ {escaped_area} "
                f"OR description ~ {escaped_area})"
            )

        # Add time filter
        clauses.append(f"created >= -{days}d")

        jql = " AND ".join(clauses) + " ORDER BY created DESC"
        logger.debug(f"Built JQL for similar tickets: {jql}")
        return jql

    @staticmethod
    def advanced_search(
        project: str = "SNOW",
        status: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        area: Optional[str] = None,
        deployment: Optional[str] = None,
        account_locator: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        order_by: str = "created DESC",
    ) -> str:
        """
        Build advanced JQL with multiple optional filters.

        Args:
            project: JIRA project (default: "SNOW")
            status: List of statuses
            assignee: Assignee username or email
            area: JIRA area
            deployment: Deployment name
            account_locator: Account locator
            created_after: Created after date (JQL format: "2025-01-01" or "-30d")
            created_before: Created before date
            order_by: Sort order (default: "created DESC")

        Returns:
            JQL query string
        """
        clauses = [f'project = "{project}"']

        if status:
            status_list = ", ".join([JQLBuilder._escape_jql_value(s) for s in status])
            clauses.append(f"status IN ({status_list})")

        if assignee:
            if assignee.lower() == "currentuser":
                clauses.append("assignee = currentUser()")
            else:
                escaped_assignee = JQLBuilder._escape_jql_value(assignee)
                clauses.append(f"assignee = {escaped_assignee}")

        if area:
            escaped_area = JQLBuilder._escape_jql_value(area)
            clauses.append(f"{CUSTOM_FIELD_AREA} ~ {escaped_area}")

        if deployment:
            escaped_deployment = JQLBuilder._escape_jql_value(deployment)
            clauses.append(f"{CUSTOM_FIELD_DEPLOYMENT} ~ {escaped_deployment}")

        if account_locator:
            escaped_account = JQLBuilder._escape_jql_value(account_locator)
            clauses.append(f"{CUSTOM_FIELD_ACCOUNT_LOCATOR} ~ {escaped_account}")

        if created_after:
            clauses.append(f"created >= {created_after}")

        if created_before:
            clauses.append(f"created <= {created_before}")

        jql = " AND ".join(clauses)

        if order_by:
            jql += f" ORDER BY {order_by}"

        logger.debug(f"Built advanced JQL: {jql}")
        return jql
