"""TruLens configuration for caching experiments.

Adapted from jsummer/langgraph-trulens metrics.py.
Includes cache-specific metrics and instrumentation.
"""
import logging
from typing import Dict, Any

from trulens.providers.cortex import Cortex
from trulens.core.feedback.custom_metric import MetricConfig
from trulens.core.feedback.selector import Selector
from trulens.otel.semconv.trace import SpanAttributes
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.core import TruSession

from shared.utils import get_snowpark_session, application_name

logger = logging.getLogger(application_name)

# Initialize Cortex LLM judge for metrics
llm_judge = Cortex(
    model_engine="claude-4-sonnet",
    snowpark_session=get_snowpark_session()
)

# TruLens Snowflake Connector
# Use regular tables instead of event tables for more reliable persistence
tru_snowflake_connector = SnowflakeConnector(
    snowpark_session=get_snowpark_session(),
    use_account_event_table=False  # Disable event tables, use regular tables
)

# Initialize TruSession with connector
# This creates necessary database tables and enables persistence
tru_session = TruSession(connector=tru_snowflake_connector)


# Built-in metric: Correctness with COT
f_correctness_with_cot_reasons = MetricConfig(
    metric_name="Correctness with COT Reasons",
    metric_implementation=llm_judge.correctness_with_cot_reasons,
    selectors={
        "text": Selector(
            span_type="record_root",
            span_attribute=SpanAttributes.RECORD_ROOT.OUTPUT
        ),
    },
    description="Evaluates correctness of answer. Does not use ground truth."
)


# Custom correctness metric using ground truth
def custom_correctness_metric(
    input_text: str,
    output_text: str,
    reference_output: str
) -> tuple[float, dict]:
    """Custom correctness metric using ground truth."""
    SYSTEM_PROMPT = """
    You are an expert evaluator assessing the correctness of AI-generated responses.

    Your task is to compare a generated response against a reference (ground truth) answer and assign a score between 0.0 and 1.0.

    Scoring Guidelines:
    - 1.0: The response is completely correct and matches the ground truth in meaning and accuracy
    - 0.8-0.9: The response is mostly correct with minor differences that don't affect the core answer
    - 0.5-0.7: The response is partially correct but missing key information or contains some inaccuracies
    - 0.2-0.4: The response has significant errors or only captures a small portion of the correct answer
    - 0.0: The response is completely incorrect or irrelevant

    Consider:
    - Semantic equivalence (different wording but same meaning should score high)
    - Factual accuracy compared to the reference
    - Completeness of the answer
    - Whether the response directly addresses the question

    Provide your reasoning and then assign a numerical score.
    """

    USER_PROMPT = """
    Question: {input_text}
    Generated Response: {output_text}
    Reference Answer: {reference_output}
    """.format(
        input_text=input_text,
        output_text=output_text,
        reference_output=reference_output
    )

    try:
        return llm_judge.generate_score_and_reasons(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT,
            min_score_val=0,
            max_score_val=10,
        )
    except Exception as e:
        logger.error(f"Error in custom correctness metric: {e}")
        return 0.0, {"reasons": f"Error: {e}"}


f_custom_correctness_metric = MetricConfig(
    metric_name="Custom Correctness Metric",
    metric_implementation=custom_correctness_metric,
    selectors={
        "input_text": Selector(
            span_type="record_root",
            span_attribute=SpanAttributes.RECORD_ROOT.INPUT
        ),
        "output_text": Selector(
            span_type="record_root",
            span_attribute=SpanAttributes.RECORD_ROOT.OUTPUT
        ),
        "reference_output": Selector(
            span_type="record_root",
            span_attribute=SpanAttributes.RECORD_ROOT.GROUND_TRUTH_OUTPUT
        ),
    },
    description="Evaluates correctness compared to ground truth using custom metric."
)


# Cache-specific metrics
def cache_hit_rate_metric(cache_hits: int, total_queries: int) -> tuple[float, dict]:
    """Calculate cache hit rate."""
    if total_queries == 0:
        return 0.0, {"reason": "No queries executed"}
    hit_rate = cache_hits / total_queries
    return hit_rate, {
        "cache_hits": cache_hits,
        "total_queries": total_queries,
        "hit_percentage": f"{hit_rate * 100:.1f}%"
    }


def latency_reduction_metric(
    cached_latency_ms: float,
    uncached_latency_ms: float
) -> tuple[float, dict]:
    """Calculate latency reduction from caching."""
    if uncached_latency_ms == 0:
        return 0.0, {"reason": "No baseline latency"}
    reduction = (uncached_latency_ms - cached_latency_ms) / uncached_latency_ms
    return reduction, {
        "cached_latency_ms": cached_latency_ms,
        "uncached_latency_ms": uncached_latency_ms,
        "reduction_percentage": f"{reduction * 100:.1f}%",
        "speedup_factor": f"{uncached_latency_ms / cached_latency_ms:.2f}x"
    }


def cost_savings_metric(
    cached_tokens: int,
    uncached_tokens: int,
    token_cost_per_1k: float = 0.003
) -> tuple[float, dict]:
    """Calculate cost savings from reduced token usage."""
    if uncached_tokens == 0:
        return 0.0, {"reason": "No baseline token usage"}
    savings_ratio = (uncached_tokens - cached_tokens) / uncached_tokens
    cost_saved = ((uncached_tokens - cached_tokens) / 1000) * token_cost_per_1k
    return savings_ratio, {
        "cached_tokens": cached_tokens,
        "uncached_tokens": uncached_tokens,
        "tokens_saved": uncached_tokens - cached_tokens,
        "savings_percentage": f"{savings_ratio * 100:.1f}%",
        "cost_saved_usd": f"${cost_saved:.4f}"
    }


# All metrics for experiments
STANDARD_METRICS = [
    f_correctness_with_cot_reasons,
    f_custom_correctness_metric,
]

CACHE_METRICS = [
    cache_hit_rate_metric,
    latency_reduction_metric,
    cost_savings_metric,
]

ALL_METRICS = STANDARD_METRICS
