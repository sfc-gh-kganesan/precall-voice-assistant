"""
P67 Workflow SDK for Python.

This package provides the WorkflowSDK class for building workflows
that interact with Snowflake and Cortex services.
"""

from p67_sdk.sdk import WorkflowSDK
from p67_sdk.types import (
    QueryResult,
    HttpResponse,
    CortexAnalystResponse,
    CortexAgentResponse,
    InterruptOptions,
    SlackTextObject,
    SlackButtonElement,
    InterruptButton,
    SlackNotifyConfig,
    # Cortex Complete types
    CortexInferenceRegion,
    CortexMessageRole,
    CortexTextContent,
    CortexImageUrl,
    CortexImageContent,
    CortexToolResultContent,
    CortexMessage,
    CortexToolFunctionParameters,
    CortexToolFunction,
    CortexTool,
    CortexToolCallFunction,
    CortexToolCall,
    CortexForcedFunction,
    CortexForcedToolChoice,
    CortexGuardrails,
    CortexCompleteOptions,
    CortexTokenUsage,
    CortexChoiceMessage,
    CortexChoice,
    CortexCompleteRequestInfo,
    CortexCompleteResponse,
    CortexStreamDeltaToolCallFunction,
    CortexStreamDeltaToolCall,
    CortexStreamDelta,
    CortexStreamChoice,
    CortexStreamChunk,
    # Cortex Code types
    CortexCodeOptions,
    CortexCodeResponse,
)
from p67_sdk.automation_context import AutomationContext
from p67_sdk.context_factory import create_context
from p67_sdk.ipc import _handle_resume_interrupt, _handle_oauth_token_response

__version__ = "0.1.0"

__all__ = [
    "WorkflowSDK",
    "AutomationContext",
    "create_context",
    "QueryResult",
    "HttpResponse",
    "CortexAnalystResponse",
    "CortexAgentResponse",
    "InterruptOptions",
    "SlackTextObject",
    "SlackButtonElement",
    "InterruptButton",
    "SlackNotifyConfig",
    "_handle_resume_interrupt",
    "_handle_oauth_token_response",
    # Cortex Complete types
    "CortexInferenceRegion",
    "CortexMessageRole",
    "CortexTextContent",
    "CortexImageUrl",
    "CortexImageContent",
    "CortexToolResultContent",
    "CortexMessage",
    "CortexToolFunctionParameters",
    "CortexToolFunction",
    "CortexTool",
    "CortexToolCallFunction",
    "CortexToolCall",
    "CortexForcedFunction",
    "CortexForcedToolChoice",
    "CortexGuardrails",
    "CortexCompleteOptions",
    "CortexTokenUsage",
    "CortexChoiceMessage",
    "CortexChoice",
    "CortexCompleteRequestInfo",
    "CortexCompleteResponse",
    "CortexStreamDeltaToolCallFunction",
    "CortexStreamDeltaToolCall",
    "CortexStreamDelta",
    "CortexStreamChoice",
    "CortexStreamChunk",
    # Cortex Code types
    "CortexCodeOptions",
    "CortexCodeResponse",
]
