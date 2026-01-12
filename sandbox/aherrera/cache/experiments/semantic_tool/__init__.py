"""Semantic tool cache experiment.

This experiment tests tool-level semantic caching where individual tool outputs
are cached based on semantic similarity of inputs. The LLM still generates plans,
but tool execution may hit cache.
"""
