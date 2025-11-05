"""
JIRA integration module for searching and managing JIRA tickets.
"""

from app.integrations.jira.client import get_jira_client, JiraClient

__all__ = ["get_jira_client", "JiraClient"]
