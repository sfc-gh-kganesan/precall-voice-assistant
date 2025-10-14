"""
Entry point for LangGraph Studio.

This module provides a clean separation between the production workflow 
and the LangGraph Studio development environment.
"""

from app.graph import create_graph

# Simple, explicit graph export for LangGraph Studio
# The graph is created once when this module is imported by Studio
graph = create_graph()

