"""Base experiment runner for caching experiments.

Provides common orchestration logic for all experiments:
- Load datasets from JSON
- Convert to DataFrame for TruLens
- Setup TruGraph with instrumentation
- Execute runs with performance tracking
- Compute and aggregate metrics
"""
import uuid
import time
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

import pandas as pd
from langchain_core.messages import HumanMessage

from trulens.connectors.snowflake import SnowflakeConnector
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes
from trulens.apps.langgraph import TruGraph
from trulens.core.run import Run, RunConfig

from shared.utils import get_snowpark_session, application_name
from shared.trulens_config import STANDARD_METRICS, tru_session
from shared.metrics_collector import PerformanceMetrics, TimedInvocation

logger = logging.getLogger(application_name)


class LanggraphWorkflow:
    """Wrapper for LangGraph to enable TruLens instrumentation.

    This wrapper pattern is required by TruLens to properly capture
    inputs, outputs, and ground truth for evaluation.
    """

    def __init__(self, graph, metrics_collector: Optional[PerformanceMetrics] = None):
        """Initialize workflow wrapper.

        Args:
            graph: Compiled LangGraph workflow
            metrics_collector: Optional PerformanceMetrics instance for tracking
        """
        self.graph = graph
        self.metrics_collector = metrics_collector

    @instrument(
        span_type=SpanAttributes.SpanType.RECORD_ROOT,
        attributes=lambda ret, exception, *args, **kwargs: {
            SpanAttributes.INPUT_ID: kwargs.get('id', str(uuid.uuid4())),
            SpanAttributes.RECORD_ROOT.INPUT: f"query={kwargs.get('query', '')}",
            SpanAttributes.RECORD_ROOT.OUTPUT: str(ret) if ret is not None else "",
            SpanAttributes.RECORD_ROOT.GROUND_TRUTH_OUTPUT: kwargs.get('reference_output', ''),
        }
    )
    def run_query(
        self,
        query: str,
        id: str = str(uuid.uuid4()),
        reference_output: str = ""
    ) -> str:
        """Main method that TruLens calls for each query.

        Args:
            query: The input query text
            id: Unique identifier for this query
            reference_output: Ground truth output for correctness evaluation

        Returns:
            The response text from the graph
        """
        logger.info(f"Processing query", extra={"query_id": id, "query": query})

        # Use performance metrics collector if available
        if self.metrics_collector:
            with TimedInvocation(self.metrics_collector, id, query) as timed:
                response, cache_hit = self._invoke_graph(query)

                # TODO: Extract token usage and tools from response/state
                # For now, set placeholders
                timed.set_response(
                    response=response,
                    tokens_used=0,  # Will implement token extraction
                    cache_hit=cache_hit,  # Now extracted from graph state
                    tools_called=[]  # Will extract from graph state
                )

                return response
        else:
            response, _ = self._invoke_graph(query)
            return response

    def _invoke_graph(self, query: str) -> tuple[str, bool]:
        """Invoke the graph with the query.

        Args:
            query: The input query text

        Returns:
            Tuple of (response text, cache_hit boolean)
        """
        state = {
            "messages": [HumanMessage(content=query)],
        }

        result = self.graph.invoke(state)

        # Extract the AIMessage content from the result
        response_text = ""
        if "messages" in result and len(result["messages"]) > 0:
            response_text = result["messages"][-1].content
        else:
            logger.warning("No response from graph")
            response_text = "No response from model"

        # Extract cache_hit from state (defaults to False if not present)
        cache_hit = result.get("cache_hit", False)

        return response_text, cache_hit


class ExperimentRunner:
    """Base class for running caching experiments with TruLens evaluation."""

    def __init__(
        self,
        experiment_name: str,
        app_version: str,
        graph,
        dataset_path: str,
        performance_collector: Optional[PerformanceMetrics] = None,
        connector: Optional[SnowflakeConnector] = None,
    ):
        """Initialize experiment runner.

        Args:
            experiment_name: Name of the experiment (e.g., "cortex-cache-baseline-llm")
            app_version: Version string for the experiment
            graph: Compiled LangGraph workflow
            dataset_path: Path to dataset JSON file
            performance_collector: PerformanceMetrics instance for tracking
            connector: TruLens SnowflakeConnector (will create if not provided)
        """
        self.experiment_name = experiment_name
        self.app_version = app_version
        self.graph = graph
        self.dataset_path = Path(dataset_path)
        self.performance_collector = performance_collector or PerformanceMetrics()

        # Setup TruLens session (use global session with connector)
        self.tru_session = tru_session
        self.connector = self.tru_session.connector

        # Create LangGraph workflow wrapper
        self.workflow = LanggraphWorkflow(self.graph, self.performance_collector)

        # Wrap with TruGraph for instrumentation
        # Note: Disable automatic background evaluator (start_evaluator=False) because:
        # 1. We explicitly call compute_metrics() after invocations complete
        # 2. Background evaluator causes run status to become FAILED
        # 3. We don't need real-time feedback during execution
        self.tru_workflow = TruGraph(
            self.workflow,
            app_name=self.experiment_name,
            app_version=self.app_version,
            connector=self.connector,
            main_method_name="run_query",
            start_evaluator=False,  # Disable automatic background evaluation
        )

        logger.info(
            f"Initialized ExperimentRunner: {experiment_name}",
            extra={
                "experiment_name": experiment_name,
                "app_version": app_version,
                "dataset_path": str(dataset_path)
            }
        )

    def load_dataset(
        self,
        use_similar_queries: bool = False
    ) -> pd.DataFrame:
        """Load dataset from JSON file and convert to DataFrame.

        Args:
            use_similar_queries: If True, expand dataset to include similar_queries

        Returns:
            Pandas DataFrame with columns: ID, QUERY, REFERENCE_OUTPUT
        """
        logger.info(f"Loading dataset from {self.dataset_path}")

        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        test_cases = data.get("test_cases", [])

        if not test_cases:
            raise ValueError(f"No test_cases found in {self.dataset_path}")

        rows = []

        for test_case in test_cases:
            # Add main query
            rows.append({
                "ID": test_case["id"],
                "QUERY": test_case["query"],
                "REFERENCE_OUTPUT": test_case["reference_output"]
            })

            # Optionally add similar queries for cache testing
            if use_similar_queries and "similar_queries" in test_case:
                for idx, similar_query in enumerate(test_case["similar_queries"]):
                    rows.append({
                        "ID": f"{test_case['id']}_similar_{idx}",
                        "QUERY": similar_query,
                        "REFERENCE_OUTPUT": test_case["reference_output"]
                    })

        df = pd.DataFrame(rows)

        logger.info(
            f"Loaded dataset with {len(df)} queries",
            extra={"total_queries": len(df), "use_similar_queries": use_similar_queries}
        )

        return df

    def run_experiment(
        self,
        use_similar_queries: bool = False,
        dataset_name: str = "cache-experiment",
        label: str = "v1.0.0",
        llm_judge_name: str = "claude-4-sonnet",
        compute_metrics: bool = True
    ) -> Dict[str, Any]:
        """Execute the experiment with TruLens evaluation.

        Args:
            use_similar_queries: Include similar queries in dataset
            dataset_name: Name for the dataset in TruLens
            label: Label/version for this run
            llm_judge_name: LLM judge model for correctness evaluation
            compute_metrics: Whether to compute TruLens metrics

        Returns:
            Dictionary containing experiment results and metrics
        """
        logger.info(f"Starting experiment: {self.experiment_name}")

        # Load dataset
        df = self.load_dataset(use_similar_queries=use_similar_queries)

        # Create run configuration
        run_name = str(uuid.uuid4())
        run_config = RunConfig(
            run_name=run_name,
            dataset_name=dataset_name,
            description=f"Experiment: {self.experiment_name}",
            label=label,
            source_type="DATAFRAME",
            dataset_spec={
                "query": "QUERY",
                "id": "ID",
                "reference_output": "REFERENCE_OUTPUT",
            },
            llm_judge_name=llm_judge_name,
        )

        logger.info(f"Created run config", extra={"run_name": run_name})

        # Add run to TruGraph
        run: Run = self.tru_workflow.add_run(run_config=run_config)

        # Start execution
        logger.info("Starting TruLens run...")
        run.start(input_df=df)

        # Wait for completion with timeout
        logger.info("Waiting for TruLens run to complete...")
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        last_status = None

        while True:
            status = run.get_status()

            # Log status changes
            if status != last_status:
                logger.info(f"Run status: {status}")
                last_status = status

            # Check if completed successfully
            if status == "INVOCATION_COMPLETED":
                break

            # Check if failed (shouldn't happen now that background evaluator is disabled)
            if status == "FAILED":
                logger.warning(
                    "TruLens run marked as FAILED. This is unexpected with background evaluator disabled."
                )
                logger.info("Continuing to retrieve invocation results...")
                break

            # Check for timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                logger.error(
                    f"Timeout waiting for completion after {elapsed:.1f}s. "
                    f"Last status: {status}"
                )
                raise TimeoutError(
                    f"Run did not complete within {max_wait_time}s. Status: {status}"
                )

            time.sleep(3)

        logger.info("TruLens run completed")

        # Compute metrics
        if compute_metrics:
            logger.info("Computing TruLens metrics...")

            # Compute TruLens correctness metrics
            # Pass MetricConfig objects directly for custom metrics, not their string names
            run.compute_metrics(metrics=STANDARD_METRICS + ["correctness"])

            # Get run records and calculate metric scores
            run_record = self.tru_workflow.get_run(run_name=run_name)
            records = run_record.get_records()

            metric_scores = {}
            # Extract metric names for aggregation
            metric_names = [m.metric_name for m in STANDARD_METRICS] + ["correctness"]
            for metric_name in metric_names:
                if metric_name in records.columns:
                    metric_scores[metric_name] = round(float(records[metric_name].mean()), 2)

            logger.info("TruLens metric scores", extra={"metric_scores": metric_scores})
        else:
            metric_scores = {}

        # Get performance metrics
        performance_metrics = self.performance_collector.get_aggregate_metrics()

        # Combine results
        results = {
            "experiment_name": self.experiment_name,
            "run_name": run_name,
            "dataset_name": dataset_name,
            "total_queries": len(df),
            "trulens_metrics": metric_scores,
            "performance_metrics": performance_metrics,
        }

        logger.info("Experiment completed", extra=results)

        return results

    def warmup_cache(self, dataset: Optional[List[dict]] = None):
        """Pre-populate cache with queries (for caching experiments).

        Args:
            dataset: Optional list of test cases. If not provided, loads from dataset_path
        """
        logger.info("Starting cache warmup...")

        if dataset is None:
            with open(self.dataset_path, 'r') as f:
                data = json.load(f)
            dataset = data.get("test_cases", [])

        # Run queries through graph without metrics collection
        for test_case in dataset:
            query = test_case["query"]
            logger.debug(f"Warmup query: {query}")

            state = {"messages": [HumanMessage(content=query)]}
            result = self.graph.invoke(state)

        logger.info(f"Cache warmup completed with {len(dataset)} queries")
