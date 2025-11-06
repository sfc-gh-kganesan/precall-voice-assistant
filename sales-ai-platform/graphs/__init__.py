"""
LangGraph workflows for the Sales AI Platform.

This package contains multiple graph implementations for different AI workflows.
Each graph file contains its own state schema for better cohesion.
"""

from graphs.graph_utils import get_llm
from graphs.post_meeting_workflow import graph as post_meeting_graph
from graphs.prompts import HUMAN_MESSAGE_SFDC_EXTRACTION, SYSTEM_PROMPT_SFDC_EXTRACTION

__all__ = [
    "post_meeting_graph",
    "SYSTEM_PROMPT_SFDC_EXTRACTION",
    "HUMAN_MESSAGE_SFDC_EXTRACTION",
    "get_llm",
]
