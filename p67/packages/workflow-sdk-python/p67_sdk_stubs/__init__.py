"""
P67 Workflow SDK for Python.

This package provides the WorkflowSDK class for building workflows
that interact with Snowflake and Cortex services.

NOTE: This is a stub package for IDE support only.
The actual implementation is bundled at build time by 'p67 build'.
"""

from p67_sdk.types import (
    QueryResult,
    HttpResponse,
    CortexAnalystResponse,
    CortexAgentResponse,
    InterruptOptions,
    EmailOptions,
    HttpRequestOptions,
    CortexAgentOptions,
)
from p67_sdk.sdk import WorkflowSDK

__version__ = "0.1.0"

__all__ = [
    "WorkflowSDK",
    "QueryResult",
    "HttpResponse",
    "CortexAnalystResponse",
    "CortexAgentResponse",
    "InterruptOptions",
    "EmailOptions",
    "HttpRequestOptions",
    "CortexAgentOptions",
]
