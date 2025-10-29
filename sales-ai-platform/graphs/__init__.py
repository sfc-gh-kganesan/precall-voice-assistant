"""
LangGraph workflows for the Sales AI Platform.

This package contains multiple graph implementations for different AI workflows.
Each graph file contains its own state schema for better cohesion.
"""

from graphs.arithmetic_agent import graph as arithmetic_graph
from graphs.greeting_workflow import graph as greeting_graph
from graphs.post_meeting_workflow import graph as post_meeting_graph
from graphs.prompts import SYSTEM_PROMPT_SFDC_EXTRACTION, HUMAN_MESSAGE_SFDC_EXTRACTION
from graphs.graph_utils import get_llm

__all__ = [
    "arithmetic_graph", 
    "greeting_graph", 
    "post_meeting_graph", 
    "SYSTEM_PROMPT_SFDC_EXTRACTION", 
    "HUMAN_MESSAGE_SFDC_EXTRACTION",
    "get_llm"
    ]

