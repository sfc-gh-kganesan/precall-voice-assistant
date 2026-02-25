"""
Type definitions for the P67 Workflow SDK.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


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


# =============================================================================
# Subworkflow Types
# =============================================================================

# Type alias for subworkflow execution status
SubworkflowStatus = Literal['completed', 'failed', 'interrupted']


@dataclass(frozen=True)
class SubworkflowOptions:
    """Options for executing a subworkflow.
    
    Exactly one of workflow_id or workflow_name must be provided.
    """
    workflow_id: Optional[str] = None  # Run by ID
    workflow_name: Optional[str] = None  # Run by name (uses latest version)
    params: Optional[Dict[str, str]] = None  # Runtime parameter overrides
    timeout: int = 300000  # Timeout in milliseconds (default 5 min)

    def __post_init__(self) -> None:
        """Validate that exactly one of workflow_id or workflow_name is provided."""
        has_id = self.workflow_id is not None and self.workflow_id != ''
        has_name = self.workflow_name is not None and self.workflow_name != ''
        if has_id and has_name:
            raise ValueError("Provide either workflow_id or workflow_name, not both")
        if not has_id and not has_name:
            raise ValueError("Either workflow_id or workflow_name is required")


@dataclass(frozen=True)
class SubworkflowResponse:
    """Response from subworkflow execution."""
    success: bool
    exit_code: Optional[int] = None
    stdout: Optional[List[str]] = None
    stderr: Optional[List[str]] = None
    status: Optional[SubworkflowStatus] = None
    run_id: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Cortex Complete Types (LLM Inference)
# =============================================================================

# Type aliases for message roles and content
CortexMessageRole = str  # 'system' | 'user' | 'assistant' | 'tool'
CortexInferenceRegion = str  # 'auto' | 'cross-cloud-any' | 'aws-global' | etc.


@dataclass
class CortexTextContent:
    """Text content block."""
    type: str  # Always 'text'
    text: str


@dataclass
class CortexImageUrl:
    """Image URL details."""
    url: str  # Base64 data URL or HTTPS URL


@dataclass
class CortexImageContent:
    """Image content block for vision models."""
    type: str  # Always 'image_url'
    image_url: CortexImageUrl


@dataclass
class CortexToolResultContent:
    """Tool result content block."""
    type: str  # Always 'tool_result'
    tool_use_id: str
    content: str


@dataclass
class CortexMessage:
    """Message in a Cortex LLM conversation."""
    role: CortexMessageRole
    content: Any  # str | List[CortexTextContent | CortexImageContent | CortexToolResultContent]
    tool_call_id: Optional[str] = None


@dataclass
class CortexToolFunctionParameters:
    """JSON Schema for tool function parameters."""
    type: str  # Always 'object'
    properties: Dict[str, Any]
    required: Optional[List[str]] = None


@dataclass
class CortexToolFunction:
    """Tool function definition."""
    name: str
    description: str
    parameters: CortexToolFunctionParameters


@dataclass
class CortexTool:
    """Tool definition for Cortex LLM."""
    type: str  # Always 'function'
    function: CortexToolFunction


@dataclass
class CortexToolCallFunction:
    """Function call details in a tool call."""
    name: str
    arguments: str  # JSON string


@dataclass
class CortexToolCall:
    """Tool call made by the model."""
    id: str
    type: str  # Always 'function'
    function: CortexToolCallFunction


@dataclass
class CortexForcedFunction:
    """Specific function to force."""
    name: str


@dataclass
class CortexForcedToolChoice:
    """Force the model to call a specific tool."""
    type: str  # Always 'function'
    function: CortexForcedFunction


# CortexToolChoice can be: 'auto' | 'none' | 'required' | CortexForcedToolChoice
CortexToolChoice = Any


@dataclass
class CortexGuardrails:
    """Cortex Guard content filtering configuration."""
    enabled: bool
    response_when_unsafe: Optional[str] = None


@dataclass
class CortexCompleteOptions:
    """Options for cortex_complete."""
    model: str
    messages: Any  # str | List[CortexMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[CortexTool]] = None
    tool_choice: Optional[CortexToolChoice] = None
    guardrails: Optional[CortexGuardrails] = None
    timeout: Optional[int] = None  # milliseconds
    region: Optional[CortexInferenceRegion] = None


@dataclass
class CortexTokenUsage:
    """Token usage statistics from Cortex LLM."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_cached: Optional[int] = None


@dataclass
class CortexChoiceMessage:
    """Generated message in a completion choice."""
    role: str  # Always 'assistant'
    content: Optional[str]
    tool_calls: Optional[List[CortexToolCall]] = None


@dataclass
class CortexChoice:
    """Choice from a Cortex LLM completion."""
    index: int
    message: CortexChoiceMessage
    finish_reason: str  # 'stop' | 'length' | 'tool_calls' | 'content_filter'


@dataclass
class CortexCompleteRequestInfo:
    """Request details for debugging."""
    url: str
    headers: Dict[str, str]  # Sanitized (no auth token)
    payload: Any


@dataclass
class CortexCompleteResponse:
    """Response from cortex_complete."""
    success: bool
    id: Optional[str] = None
    model: Optional[str] = None
    choices: Optional[List[CortexChoice]] = None
    usage: Optional[CortexTokenUsage] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    request: Optional[CortexCompleteRequestInfo] = None


# =============================================================================
# Cortex Complete Streaming Types
# =============================================================================

@dataclass
class CortexStreamDeltaToolCallFunction:
    """Function details in a streaming tool call delta."""
    name: Optional[str] = None
    arguments: Optional[str] = None


@dataclass
class CortexStreamDeltaToolCall:
    """Tool call delta in a streaming chunk."""
    index: int
    id: Optional[str] = None
    type: Optional[str] = None
    function: Optional[CortexStreamDeltaToolCallFunction] = None


@dataclass
class CortexStreamDelta:
    """Delta content in a streaming chunk."""
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[CortexStreamDeltaToolCall]] = None


@dataclass
class CortexStreamChoice:
    """Choice in a streaming chunk."""
    index: int
    delta: CortexStreamDelta
    finish_reason: Optional[str] = None  # 'stop' | 'length' | 'tool_calls' | 'content_filter' | None


@dataclass
class CortexStreamChunk:
    """Streaming chunk from cortex_complete_stream."""
    id: str
    object: str  # Always 'chat.completion.chunk'
    created: int
    model: str
    choices: List[CortexStreamChoice]
    usage: Optional[CortexTokenUsage] = None
