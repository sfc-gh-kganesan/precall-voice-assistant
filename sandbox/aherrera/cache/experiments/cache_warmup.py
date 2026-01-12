"""Cache warmup utilities for caching experiments.

Provides functions to pre-populate caches with initial queries
before running experiments to test cache effectiveness.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_core.messages import HumanMessage

from shared.utils import application_name
from shared.cache_backends import CortexSearchCache, PlanCache, ToolCache

logger = logging.getLogger(application_name)


def warmup_cache(
    graph,
    dataset: List[dict],
    cache_backend: Optional[Any] = None,
    skip_similar_queries: bool = True
) -> Dict[str, Any]:
    """Pre-populate cache with queries from dataset.

    Args:
        graph: Compiled LangGraph workflow
        dataset: List of test case dictionaries with 'query' and 'reference_output'
        cache_backend: Optional cache backend to inspect (for statistics)
        skip_similar_queries: If True, only use main queries, not similar_queries

    Returns:
        Dictionary with warmup statistics:
        - queries_processed
        - cache_entries_created
        - errors (if any)
    """
    logger.info(f"Starting cache warmup with {len(dataset)} test cases")

    queries_processed = 0
    errors = []

    for test_case in dataset:
        query = test_case.get("query")
        if not query:
            logger.warning(f"Skipping test case without query: {test_case.get('id')}")
            continue

        try:
            # Invoke graph to populate cache
            state = {"messages": [HumanMessage(content=query)]}
            result = graph.invoke(state)

            queries_processed += 1

            logger.debug(
                f"Warmup query processed",
                extra={
                    "query_id": test_case.get("id"),
                    "query": query[:50] + "..." if len(query) > 50 else query
                }
            )

        except Exception as e:
            error_msg = f"Error processing query {test_case.get('id')}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Get cache statistics if backend provided
    cache_stats = {}
    if cache_backend:
        try:
            if isinstance(cache_backend, CortexSearchCache):
                # Query Cortex Search to get entry count
                # This is a placeholder - actual implementation depends on cache backend
                cache_stats["cache_type"] = "CortexSearchCache"
                cache_stats["similarity_threshold"] = cache_backend.similarity_threshold
            elif isinstance(cache_backend, PlanCache):
                cache_stats["cache_type"] = "PlanCache"
            elif isinstance(cache_backend, ToolCache):
                cache_stats["cache_type"] = "ToolCache"
        except Exception as e:
            logger.warning(f"Could not get cache statistics: {e}")

    stats = {
        "queries_processed": queries_processed,
        "total_test_cases": len(dataset),
        "errors": errors,
        "cache_stats": cache_stats
    }

    logger.info("Cache warmup completed", extra=stats)

    return stats


def warmup_from_dataset_file(
    graph,
    dataset_path: str,
    cache_backend: Optional[Any] = None
) -> Dict[str, Any]:
    """Load dataset from JSON file and warmup cache.

    Args:
        graph: Compiled LangGraph workflow
        dataset_path: Path to dataset JSON file
        cache_backend: Optional cache backend to inspect

    Returns:
        Dictionary with warmup statistics
    """
    logger.info(f"Loading dataset from {dataset_path} for warmup")

    with open(dataset_path, 'r') as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])

    if not test_cases:
        raise ValueError(f"No test_cases found in {dataset_path}")

    return warmup_cache(graph, test_cases, cache_backend)


def warmup_with_similar_queries(
    graph,
    dataset: List[dict],
    cache_backend: Optional[Any] = None
) -> Dict[str, Any]:
    """Warmup cache including similar queries from dataset.

    This is useful for testing semantic cache effectiveness by pre-populating
    with main queries, then testing with similar variations.

    Args:
        graph: Compiled LangGraph workflow
        dataset: List of test case dictionaries
        cache_backend: Optional cache backend to inspect

    Returns:
        Dictionary with warmup statistics
    """
    logger.info("Warming up cache with main queries only (similar queries saved for testing)")

    # First warmup with main queries
    main_stats = warmup_cache(graph, dataset, cache_backend, skip_similar_queries=True)

    # Count similar queries available for testing
    similar_query_count = 0
    for test_case in dataset:
        similar_queries = test_case.get("similar_queries", [])
        similar_query_count += len(similar_queries)

    main_stats["similar_queries_available_for_testing"] = similar_query_count

    logger.info(
        "Cache warmup strategy complete",
        extra={
            "main_queries_processed": main_stats["queries_processed"],
            "similar_queries_available": similar_query_count
        }
    )

    return main_stats


def verify_cache_warmup(
    graph,
    test_query: str,
    cache_backend: Optional[Any] = None
) -> Dict[str, Any]:
    """Verify cache is warmed up by running a test query.

    Args:
        graph: Compiled LangGraph workflow
        test_query: Query to test
        cache_backend: Optional cache backend to check

    Returns:
        Dictionary with verification results
    """
    logger.info(f"Verifying cache warmup with test query: {test_query}")

    try:
        state = {"messages": [HumanMessage(content=test_query)]}
        result = graph.invoke(state)

        verification = {
            "success": True,
            "test_query": test_query,
            "response_received": "messages" in result and len(result["messages"]) > 0
        }

        if cache_backend and hasattr(cache_backend, 'get_stats'):
            verification["cache_stats"] = cache_backend.get_stats()

        logger.info("Cache warmup verification successful", extra=verification)

        return verification

    except Exception as e:
        logger.error(f"Cache warmup verification failed: {e}")
        return {
            "success": False,
            "test_query": test_query,
            "error": str(e)
        }
