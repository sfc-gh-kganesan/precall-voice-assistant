"""Full cache experiment runner for Cortex LLM.

Tests combined semantic caching at both plan and tool levels:
- Plan Cache: Caches LLM tool call decisions
- Tool Cache: Caches tool execution results

This represents maximum caching strategy.
"""
import logging
import argparse
import json
from pathlib import Path
from langchain_core.messages import HumanMessage

from shared.utils import application_name, setup_tracing
from shared.metrics_collector import PerformanceMetrics
from experiments.base_runner import ExperimentRunner
from experiments.semantic_full.graph_llm import create_full_cache_graph

logger = logging.getLogger(application_name)


def warmup_full_cache_from_dataset(graph, dataset_path: str):
    """Pre-populate both plan and tool caches from dataset.

    Args:
        graph: Compiled LangGraph workflow with caching enabled
        dataset_path: Path to dataset JSON file
    """
    logger.info("=" * 80)
    logger.info("FULL CACHE WARMUP: Pre-populating plan and tool caches")
    logger.info("=" * 80)

    with open(dataset_path, 'r') as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])

    logger.info(f"Warming up caches with {len(test_cases)} queries...")

    for idx, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        logger.info(f"  [{idx}/{len(test_cases)}] Warming up: {query[:50]}...")

        state = {
            "messages": [HumanMessage(content=query)],
            "plan_cache_hit": False,
            "tool_cache_hits": {},
            "cache_enabled": True
        }
        try:
            graph.invoke(state)
        except Exception as e:
            logger.warning(f"Warmup query failed: {e}")

    logger.info(f"Cache warmup completed with {len(test_cases)} queries")
    logger.info("=" * 80)


def run_full_cache_experiment(
    dataset_path: str = "datasets/math_operations.json",
    use_similar_queries: bool = False,
    label: str = "full-cache-v1.0.0",
    enable_plan_cache: bool = True,
    enable_tool_cache: bool = True,
    warmup_cache: bool = True,
    similarity_threshold: float = 0.85
):
    """Run full cache experiment with both plan and tool caching.

    Args:
        dataset_path: Path to dataset JSON file
        use_similar_queries: Whether to include similar_queries in dataset
        label: Label for this experimental run
        enable_plan_cache: Whether to enable plan caching
        enable_tool_cache: Whether to enable tool caching
        warmup_cache: Whether to pre-populate caches before experiment
        similarity_threshold: Minimum similarity score for cache hit (0.0-1.0)

    Returns:
        Dictionary with experiment results
    """
    logger.info("=" * 80)
    logger.info("FULL CACHE EXPERIMENT: Cortex LLM with Plan + Tool Caching")
    logger.info("=" * 80)
    logger.info(f"Plan cache enabled: {enable_plan_cache}")
    logger.info(f"Tool cache enabled: {enable_tool_cache}")
    logger.info(f"Warmup cache: {warmup_cache}")
    logger.info(f"Similarity threshold: {similarity_threshold}")
    logger.info("=" * 80)

    # Setup tracing
    setup_tracing()

    # Create graph with both caching layers
    logger.info("Creating LangGraph workflow with full caching...")
    graph = create_full_cache_graph(
        enable_plan_cache=enable_plan_cache,
        enable_tool_cache=enable_tool_cache,
        similarity_threshold=similarity_threshold
    )

    # Warmup caches if requested
    if warmup_cache and (enable_plan_cache or enable_tool_cache):
        warmup_full_cache_from_dataset(graph, dataset_path)

    # Setup performance metrics collector
    performance_collector = PerformanceMetrics(token_cost_per_1k=0.003)

    # Create experiment runner
    runner = ExperimentRunner(
        experiment_name="cortex-cache-full",
        app_version="0.1.0",
        graph=graph,
        dataset_path=dataset_path,
        performance_collector=performance_collector
    )

    # Run experiment
    logger.info(f"Running experiment with dataset: {dataset_path}")
    results = runner.run_experiment(
        use_similar_queries=use_similar_queries,
        dataset_name="cache-full-math",
        label=label,
        llm_judge_name="claude-4-sonnet",
        compute_metrics=True
    )

    # Log results summary
    logger.info("=" * 80)
    logger.info("FULL CACHE EXPERIMENT RESULTS")
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

    # Multi-level cache metrics
    if 'plan_cache_hit_rate' in perf:
        logger.info(f"  Plan Cache Hit Rate: {perf['plan_cache_hit_rate'] * 100:.1f}%")
    if 'tool_cache_hit_rate' in perf:
        logger.info(f"  Tool Cache Hit Rate: {perf['tool_cache_hit_rate'] * 100:.1f}%")

    logger.info(f"  Avg Latency: {perf['avg_latency_ms']} ms")
    logger.info(f"  P95 Latency: {perf['p95_latency_ms']} ms")
    logger.info(f"  Total Tokens: {perf['total_tokens']}")
    logger.info(f"  Cost Estimate: ${perf['cost_estimate_usd']}")
    logger.info("=" * 80)

    return results


def main():
    """Main entry point for full cache experiment."""
    parser = argparse.ArgumentParser(
        description="Run full cache experiment with Cortex LLM"
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
        default="full-cache-v1.0.0",
        help="Label for this experimental run"
    )
    parser.add_argument(
        "--no-plan-cache",
        action="store_true",
        help="Disable plan caching"
    )
    parser.add_argument(
        "--no-tool-cache",
        action="store_true",
        help="Disable tool caching"
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
        results = run_full_cache_experiment(
            dataset_path=args.dataset,
            use_similar_queries=args.use_similar_queries,
            label=args.label,
            enable_plan_cache=not args.no_plan_cache,
            enable_tool_cache=not args.no_tool_cache,
            warmup_cache=not args.no_warmup,
            similarity_threshold=args.similarity_threshold
        )

        logger.info("Full cache experiment completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Full cache experiment failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
