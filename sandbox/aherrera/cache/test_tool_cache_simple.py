#!/usr/bin/env python
"""Simple test script for tool cache - forces fresh import."""
import sys
import json
from langchain_core.messages import HumanMessage

# Force fresh import by clearing cache
if 'experiments.semantic_tool.graph_llm' in sys.modules:
    del sys.modules['experiments.semantic_tool.graph_llm']

from experiments.semantic_tool.graph_llm import create_tool_cache_graph

print("="*80)
print("Testing Tool Cache Implementation")
print("="*80)

# Create graph with caching enabled
graph = create_tool_cache_graph(
    cache_enabled=True,
    similarity_threshold=0.85
)

print("\n1. Running first query: 'What is 5 plus 3?'")
state1 = {
    "messages": [HumanMessage(content="What is 5 plus 3?")],
    "tool_cache_hits": {},
    "cache_enabled": True
}
result1 = graph.invoke(state1)
print(f"Result: {result1['messages'][-1].content}")

print("\n2. Running second query: 'Multiply 4 by 2'")
state2 = {
    "messages": [HumanMessage(content="Multiply 4 by 2")],
    "tool_cache_hits": {},
    "cache_enabled": True
}
result2 = graph.invoke(state2)
print(f"Result: {result2['messages'][-1].content}")

print("\n" + "="*80)
print("Test completed successfully!")
print("="*80)
