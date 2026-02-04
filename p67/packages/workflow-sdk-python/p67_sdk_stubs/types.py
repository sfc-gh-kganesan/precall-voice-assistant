"""
Type definitions for the P67 Workflow SDK.

These types are used for IDE autocompletion and type checking.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QueryResult:
    """Result from a SQL query execution."""
    statement: Any
    """The cursor/statement object from the query."""
    rows: List[Any]
    """List of rows returned by the query."""


@dataclass
class HttpResponse:
    """Response from an HTTP request."""
    success: bool
    """Whether the request was successful."""
    status: int
    """HTTP status code."""
    headers: Dict[str, str]
    """Response headers."""
    data: Optional[Any] = None
    """Response body (parsed as JSON if applicable)."""
    error: Optional[str] = None
    """Error message if request failed."""


@dataclass
class CortexAnalystResponse:
    """Response from Cortex Analyst."""
    success: bool
    """Whether the query was successful."""
    data: Optional[Any] = None
    """Response data from Cortex Analyst."""
    error: Optional[str] = None
    """Error message if query failed."""


@dataclass
class CortexAgentResponse:
    """Response from Cortex Agent."""
    success: bool
    """Whether the call was successful."""
    status_code: int
    """HTTP status code from the API."""
    data: Optional[Any] = None
    """Response data containing the agent's message."""
    error: Optional[str] = None
    """Error message if call failed."""
    request: Optional[Dict[str, Any]] = None
    """The original request payload (for debugging)."""


@dataclass
class InterruptOptions:
    """Options for interrupt calls."""
    timeout: Optional[int] = None
    """Timeout in milliseconds. None means wait indefinitely."""
    node_id: Optional[str] = None
    """Optional node identifier for the interrupt."""


@dataclass
class EmailOptions:
    """Options for sending email."""
    email_addresses: List[str]
    """List of recipient email addresses."""
    subject: str
    """Email subject line."""
    body: str
    """Email body content."""
    content_type: str = "text/plain"
    """MIME type of the body (text/plain or text/html)."""
    integration_name: Optional[str] = None
    """Snowflake email integration name. If not provided, uses config default."""


@dataclass
class HttpRequestOptions:
    """Options for HTTP requests."""
    url: str
    """The URL to request."""
    method: str = "GET"
    """HTTP method (GET, POST, PUT, DELETE, etc.)."""
    headers: Dict[str, str] = field(default_factory=dict)
    """Request headers."""
    body: Optional[Any] = None
    """Request body. Dict/list will be JSON-encoded."""
    oauth_ref: Optional[str] = None
    """OAuth reference for authentication."""
    timeout: int = 30000
    """Request timeout in milliseconds."""


@dataclass
class CortexAgentOptions:
    """Options for calling Cortex Agent."""
    agent_database: Optional[str] = None
    """Database containing the agent. Defaults to config database."""
    agent_schema: Optional[str] = None
    """Schema containing the agent. Defaults to config schema."""
    agent_name: Optional[str] = None
    """Name of the Cortex Agent to call."""
    parent_message_id: Optional[str] = None
    """Parent message ID for conversation context."""
