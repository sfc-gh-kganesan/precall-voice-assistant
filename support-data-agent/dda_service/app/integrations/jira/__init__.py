"""
JIRA integration module for searching and managing JIRA tickets.
"""

from app.integrations.jira.client import JiraClient, get_jira_client

__all__ = ["get_jira_client", "JiraClient"]
