"""
LangGraph workflows for the Sales AI Platform.

This package contains multiple graph implementations for different AI workflows.
Each graph file contains its own state schema for better cohesion.
"""

from graphs.arithmetic_agent import graph as arithmetic_graph
from graphs.greeting_workflow import graph as greeting_graph

__all__ = ["arithmetic_graph", "greeting_graph"]

