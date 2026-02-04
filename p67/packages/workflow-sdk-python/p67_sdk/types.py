"""
Type definitions for the P67 Workflow SDK.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QueryResult:
    """Result from a SQL query execution."""
    statement: Any
    rows: List[Any]


@dataclass
class HttpResponse:
    """Response from an HTTP request."""
    success: bool
    status: int
    headers: Dict[str, str]
    data: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class CortexAnalystResponse:
    """Response from Cortex Analyst."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class CortexAgentResponse:
    """Response from Cortex Agent."""
    success: bool
    status_code: int
    data: Optional[Any] = None
    error: Optional[str] = None
    request: Optional[Dict[str, Any]] = None


@dataclass
class InterruptOptions:
    """Options for interrupt calls."""
    timeout: Optional[int] = None  # Timeout in milliseconds
    node_id: Optional[str] = None  # Optional node identifier


@dataclass
class EmailOptions:
    """Options for sending email."""
    email_addresses: List[str]
    subject: str
    body: str
    content_type: str = "text/plain"
    integration_name: Optional[str] = None


@dataclass
class HttpRequestOptions:
    """Options for HTTP requests."""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Any] = None
    oauth_ref: Optional[str] = None
    timeout: int = 30000  # milliseconds


@dataclass 
class CortexAgentOptions:
    """Options for calling Cortex Agent."""
    agent_database: Optional[str] = None
    agent_schema: Optional[str] = None
    agent_name: Optional[str] = None
    parent_message_id: Optional[str] = None
