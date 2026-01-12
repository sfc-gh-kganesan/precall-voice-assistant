"""Tool cache experiment runner for Cortex LLM with semantic tool caching.

This experiment tests tool-level caching performance using Snowflake Cortex Search Service for:
- Tool cache hit rate (semantic similarity matching on tool inputs)
- Latency improvements (faster when tools hit cache)
- Reduced tool executions
- Cost comparisons

The LLM still generates plans, but individual tool executions may hit cache.
Results will be compared against the baseline experiment.
"""
import logging
import argparse
import json
from pathlib import Path
from langchain_core.messages import HumanMessage

from shared.utils import application_name, setup_tracing
from shared.metrics_collector import PerformanceMetrics
from experiments.base_runner import ExperimentRunner
from experiments.semantic_tool.graph_llm import create_tool_cache_graph

logger = logging.getLogger(application_name)


def warmup_tool_cache_from_dataset(graph, dataset_path: str):
    """Pre-populate tool cache by running all queries in dataset.

    Args:
        graph: Compiled LangGraph workflow with tool caching enabled
        dataset_path: Path to dataset JSON file
    """
    logger.info("=" * 80)
    logger.info("TOOL CACHE WARMUP: Pre-populating tool cache")
    logger.info("=" * 80)

    with open(dataset_path, 'r') as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])

    logger.info(f"Warming up tool cache with {len(test_cases)} queries...")

    for idx, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        logger.info(f"  [{idx}/{len(test_cases)}] Warming up: {query[:50]}...")

        state = {
            "messages": [HumanMessage(content=query)],
            "tool_cache_hits": {},
            "cache_enabled": True
        }
        try:
            graph.invoke(state)
        except Exception as e:
            logger.warning(f"Warmup query failed: {e}")

    logger.info(f"Tool cache warmup completed with {len(test_cases)} queries")
    logger.info("=" * 80)


def run_tool_cache_experiment(
    dataset_path: str = "datasets/math_operations.json",
    use_similar_queries: bool = False,
    label: str = "tool-cache-v1.0.0",
    enable_cache: bool = True,
    warmup_cache: bool = True,
    similarity_threshold: float = 0.85
):
    """Run tool cache experiment with Cortex LLM.

    Args:
        dataset_path: Path to dataset JSON file
        use_similar_queries: Whether to include similar_queries in dataset
        label: Label for this experimental run
        enable_cache: Whether to enable tool caching
        warmup_cache: Whether to pre-populate tool cache before experiment
        similarity_threshold: Minimum similarity score for cache hit (0.0-1.0)

    Returns:
        Dictionary with experiment results
    """
    logger.info("=" * 80)
    logger.info("TOOL CACHE EXPERIMENT: Cortex LLM with Semantic Tool Caching")
    logger.info("=" * 80)
    logger.info(f"Cache enabled: {enable_cache}")
    logger.info(f"Warmup cache: {warmup_cache}")
    logger.info(f"Similarity threshold: {similarity_threshold}")
    logger.info("=" * 80)

    # Setup tracing
    setup_tracing()

    # Create graph with tool caching
    logger.info("Creating LangGraph workflow with tool cache...")
    graph = create_tool_cache_graph(
        cache_enabled=enable_cache,
        similarity_threshold=similarity_threshold
    )

    # Warmup cache if requested
    if warmup_cache and enable_cache:
        warmup_tool_cache_from_dataset(graph, dataset_path)

    # Setup performance metrics collector
    performance_collector = PerformanceMetrics(token_cost_per_1k=0.003)

    # Create experiment runner
    runner = ExperimentRunner(
        experiment_name="cortex-cache-tool",
        app_version="0.1.0",
        graph=graph,
        dataset_path=dataset_path,
        performance_collector=performance_collector
    )

    # Run experiment
    logger.info(f"Running experiment with dataset: {dataset_path}")
    results = runner.run_experiment(
        use_similar_queries=use_similar_queries,
        dataset_name="cache-tool-math",
        label=label,
        llm_judge_name="claude-4-sonnet",
        compute_metrics=True
    )

    # Log results summary
    logger.info("=" * 80)
    logger.info("TOOL CACHE EXPERIMENT RESULTS")
    logger.info("=" * 80)
    logger.info(f"Experiment: {results['experiment_name']}")
    logger.info(f"Run ID: {results['run_name']}")
    logger.info(f"Total Queries: {results['total_queries']}")
    logger.info("")
    logger.info("TruLens Metrics (Correctness):")
    for metric_name, score in results['trulens_metrics'].items():
        logger.info(f"  {metric_name}: {score}")
    logger.info("")
    logger.info("Performance Metrics:")
    perf = results['performance_metrics']

    # Tool cache specific metrics
    if 'tool_cache_hit_rate' in perf:
        logger.info(f"  Tool Cache Hit Rate: {perf['tool_cache_hit_rate'] * 100:.1f}%")
        logger.info(f"  Tool Cache Hits: {perf.get('tool_cache_hits', 0)}")
        logger.info(f"  Tool Cache Misses: {perf.get('tool_cache_misses', 0)}")

    logger.info(f"  Avg Latency: {perf['avg_latency_ms']} ms")
    logger.info(f"  P95 Latency: {perf['p95_latency_ms']} ms")
    logger.info(f"  Total Tokens: {perf['total_tokens']}")
    logger.info(f"  Cost Estimate: ${perf['cost_estimate_usd']}")
    logger.info("=" * 80)

    return results


def main():
    """Main entry point for tool cache experiment."""
    parser = argparse.ArgumentParser(
        description="Run tool cache experiment with Cortex LLM"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="datasets/math_operations.json",
        help="Path to dataset JSON file"
    )
    parser.add_argument(
        "--use-similar-queries",
        action="store_true",
        help="Include similar_queries in dataset for testing"
    )
    parser.add_argument(
        "--label",
        type=str,
        default="tool-cache-v1.0.0",
        help="Label for this experimental run"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (for comparison)"
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip cache warmup step"
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.85,
        help="Minimum similarity score for cache hit (0.0-1.0)"
    )

    args = parser.parse_args()

    try:
        results = run_tool_cache_experiment(
            dataset_path=args.dataset,
            use_similar_queries=args.use_similar_queries,
            label=args.label,
            enable_cache=not args.no_cache,
            warmup_cache=not args.no_warmup,
            similarity_threshold=args.similarity_threshold
        )

        logger.info("Tool cache experiment completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Tool cache experiment failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
