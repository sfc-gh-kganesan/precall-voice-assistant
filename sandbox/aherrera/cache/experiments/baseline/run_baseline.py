"""Baseline experiment runner for Cortex LLM (no caching).

This establishes baseline performance metrics for:
- Correctness (via TruLens)
- Latency
- Token usage
- Cost

All caching experiments will be compared against this baseline.
"""
import logging
import argparse
from pathlib import Path

from shared.utils import application_name, setup_tracing
from shared.metrics_collector import PerformanceMetrics
from experiments.base_runner import ExperimentRunner
from experiments.baseline.graph_llm import create_graph

logger = logging.getLogger(application_name)


def run_baseline_experiment(
    dataset_path: str = "datasets/math_operations.json",
    use_similar_queries: bool = False,
    label: str = "baseline-v1.0.0"
):
    """Run baseline experiment with Cortex LLM.

    Args:
        dataset_path: Path to dataset JSON file
        use_similar_queries: Whether to include similar_queries in dataset
        label: Label for this experimental run

    Returns:
        Dictionary with experiment results
    """
    logger.info("=" * 80)
    logger.info("BASELINE EXPERIMENT: Cortex LLM (No Caching)")
    logger.info("=" * 80)

    # Setup tracing
    setup_tracing()

    # Create graph (no caching)
    logger.info("Creating LangGraph workflow...")
    graph = create_graph()

    # Setup performance metrics collector
    performance_collector = PerformanceMetrics(token_cost_per_1k=0.003)

    # Create experiment runner
    runner = ExperimentRunner(
        experiment_name="cortex-cache-baseline-llm",
        app_version="0.1.0",
        graph=graph,
        dataset_path=dataset_path,
        performance_collector=performance_collector
    )

    # Run experiment
    logger.info(f"Running experiment with dataset: {dataset_path}")
    results = runner.run_experiment(
        use_similar_queries=use_similar_queries,
        dataset_name="cache-baseline-math",
        label=label,
        llm_judge_name="claude-4-sonnet",
        compute_metrics=True
    )

    # Log results summary
    logger.info("=" * 80)
    logger.info("BASELINE EXPERIMENT RESULTS")
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
    logger.info(f"  Avg Latency: {perf['avg_latency_ms']} ms")
    logger.info(f"  P95 Latency: {perf['p95_latency_ms']} ms")
    logger.info(f"  Total Tokens: {perf['total_tokens']}")
    logger.info(f"  Cost Estimate: ${perf['cost_estimate_usd']}")
    logger.info("=" * 80)

    return results


def main():
    """Main entry point for baseline experiment."""
    parser = argparse.ArgumentParser(
        description="Run baseline caching experiment with Cortex LLM"
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
        default="baseline-v1.0.0",
        help="Label for this experimental run"
    )

    args = parser.parse_args()

    try:
        results = run_baseline_experiment(
            dataset_path=args.dataset,
            use_similar_queries=args.use_similar_queries,
            label=args.label
        )

        logger.info("Baseline experiment completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Baseline experiment failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
