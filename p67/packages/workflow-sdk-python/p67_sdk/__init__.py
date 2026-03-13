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
from p67_sdk.ipc import _handle_resume_interrupt

__version__ = "0.1.0"

__all__ = [
    "WorkflowSDK",
    "QueryResult",
    "HttpResponse",
    "CortexAnalystResponse",
    "CortexAgentResponse",
    "InterruptOptions",
    "_handle_resume_interrupt",
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
