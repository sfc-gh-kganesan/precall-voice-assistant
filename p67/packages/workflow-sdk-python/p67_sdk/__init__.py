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
]
