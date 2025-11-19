from trulens.providers.cortex import Cortex
from trulens.core.feedback.custom_metric import MetricConfig
from trulens.core.feedback.selector import Selector
from trulens.otel.semconv.trace import SpanAttributes

from utils import get_snowpark_session

# Initialize Cortex LLM judge
llm_judge = Cortex(
    model_engine="claude-4-sonnet", snowpark_session=get_snowpark_session()
)
# MetricConfig are client-side metrics
# Custom correctness metric using ground truth
f_correctness_with_cot_reasons = MetricConfig(
    metric_name="Correctness with COT Reasons",
    metric_implementation=llm_judge.correctness_with_cot_reasons,
    selectors={
        "text": Selector(span_type="record_root", span_attribute=SpanAttributes.RECORD_ROOT.OUTPUT),
    },
    description="Evaluates correctness of answer. Does not use ground truth."
)

def custom_correctness_metric(input_text: str, output_text: str, reference_output: str) -> tuple[float, dict]:
    """
    Custom correctness metric using ground truth
    """
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
    """.format(input_text=input_text, output_text=output_text, reference_output=reference_output)
    
    try:
        return llm_judge.generate_score_and_reasons(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT,
            min_score_val = 0,
            max_score_val = 10, # Score is normalized from 0-1 if we put 0-10 range here.
        )
    except Exception as e:
        return 0.0, {"reasons": f"Error in custom correctness metric: {e}"}


f_custom_correctness_metric = MetricConfig(
    metric_name="Custom Correctness Metric",
    metric_implementation=custom_correctness_metric,
    selectors={
        "input_text": Selector(span_type="record_root", span_attribute=SpanAttributes.RECORD_ROOT.INPUT),
        "output_text": Selector(span_type="record_root", span_attribute=SpanAttributes.RECORD_ROOT.OUTPUT),
        "reference_output": Selector(span_type="record_root", span_attribute=SpanAttributes.RECORD_ROOT.GROUND_TRUTH_OUTPUT),
    },
    description="Evaluates correctness of answer compared to ground truth using custom metric."
)

METRICS = [
    f_correctness_with_cot_reasons,
    f_custom_correctness_metric,
]