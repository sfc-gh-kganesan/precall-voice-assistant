#!/usr/bin/env python
"""Simple runner for caching experiments.

Usage:
    python run.py baseline
    python run.py baseline --use-similar-queries
    python run.py plan-cache --threshold 0.85
    python run.py semantic-full --threshold 0.90
"""
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import argparse
from experiments.baseline.run_baseline import run_baseline_experiment


def main():
    """Main entry point for experiment runner."""
    parser = argparse.ArgumentParser(
        description="Run caching experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py baseline
  python run.py baseline --use-similar-queries
  python run.py baseline --dataset datasets/data_analysis.json
  python run.py plan-cache --threshold 0.85
  python run.py semantic-full --threshold 0.90
        """
    )

    parser.add_argument(
        "experiment",
        choices=["baseline", "plan-cache", "semantic-full", "semantic-tool"],
        help="Which experiment to run"
    )

    parser.add_argument(
        "--dataset",
        default="datasets/math_operations.json",
        help="Dataset to use (default: datasets/math_operations.json)"
    )

    parser.add_argument(
        "--use-similar-queries",
        action="store_true",
        help="Include similar queries in dataset for cache testing"
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Similarity threshold for caching experiments (default: 0.85)"
    )

    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Label for this experimental run (default: auto-generated)"
    )

    args = parser.parse_args()

    try:
        if args.experiment == "baseline":
            label = args.label or f"baseline-v1.0.0"
            run_baseline_experiment(
                dataset_path=args.dataset,
                use_similar_queries=args.use_similar_queries,
                label=label
            )

        elif args.experiment == "plan-cache":
            print(f"Plan cache experiment not yet implemented")
            print(f"Will use threshold: {args.threshold}")
            return 1

        elif args.experiment == "semantic-full":
            print(f"Semantic full bypass experiment not yet implemented")
            print(f"Will use threshold: {args.threshold}")
            return 1

        elif args.experiment == "semantic-tool":
            print(f"Semantic tool cache experiment not yet implemented")
            print(f"Will use threshold: {args.threshold}")
            return 1

        print(f"\n✅ Experiment '{args.experiment}' completed successfully!")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Experiment interrupted by user")
        return 130

    except Exception as e:
        print(f"\n❌ Experiment '{args.experiment}' failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
