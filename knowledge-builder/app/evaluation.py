"""LLM-as-a-Judge evaluation module for Cortex Search quality assessment."""

import json
import time
from dataclasses import dataclass

import altair as alt
import pandas as pd
import streamlit as st
from data_operations import SnowflakeDataOperations
from trulens.providers.cortex import Cortex
from ui_utils import render_carousel_nav, render_reasoning, to_metric_key

EVALUATION_MODELS = ("llama3.1-70b", "llama3.1-405b", "mistral-large2", "claude-3-5-sonnet")
METRIC_OPTIONS = ("Context Relevance",)
MAX_CONTEXT_LENGTH = 4000
DEFAULT_RETRIES = 3
BASE_RETRY_DELAY = 2.0


def _get_metric_evaluator(metric: str):
    """Return the TruLens evaluator function for a given metric."""
    evaluators = {
        "Context Relevance": lambda p, row: p.context_relevance_with_cot_reasons(question=row["query"], context=row["context"], temperature=0.0),
    }
    return evaluators.get(metric)


def truncate_context(context: str, max_length: int = MAX_CONTEXT_LENGTH) -> str:
    """Truncate context to avoid JSON parsing issues with very long inputs."""
    if len(context) <= max_length:
        return context
    return context[:max_length] + "\n\n[Context truncated for evaluation...]"


def evaluate_metric(
    provider: Cortex,
    metric: str,
    row: pd.Series,
    max_retries: int = DEFAULT_RETRIES,
) -> tuple[float, dict, str | None]:
    """Evaluate a metric with retry logic for transient JSON errors.

    Returns:
        Tuple of (score, reasons_dict, error_message or None)
    """
    evaluator = _get_metric_evaluator(metric)
    if not evaluator:
        return 0.0, {}, f"Unknown metric: {metric}"

    last_error = None
    for attempt in range(max_retries):
        try:
            score, reasons = evaluator(provider, row)
            return float(score), reasons, None
        except Exception as e:
            last_error = str(e)
            if "json" in last_error.lower() and attempt < max_retries - 1:
                time.sleep(BASE_RETRY_DELAY * (2**attempt))
                continue
            break

    return 0.0, {"error": last_error}, last_error


def parse_evaluation_data(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the EVALUATION variant column to extract context_relevance metrics.

    Expected format: {"context_relevance": {"score": float, "reasons": {...}}}
    """
    df = df.copy()
    df.columns = df.columns.str.lower()

    if "evaluation" not in df.columns:
        return df

    metrics_data, reasons_data = [], []

    for eval_val in df["evaluation"]:
        if isinstance(eval_val, str):
            eval_data = json.loads(eval_val)
        else:
            eval_data = eval_val or {}

        if isinstance(eval_data, dict) and "context_relevance" in eval_data:
            cr = eval_data["context_relevance"]
            metrics_data.append({"context_relevance": cr.get("score")})
            reasons_data.append({"context_relevance": cr.get("reasons", {})})
        else:
            metrics_data.append({})
            reasons_data.append({})

    metrics_df = pd.json_normalize(metrics_data)
    df["reasons"] = reasons_data

    for col in metrics_df.columns:
        df[col] = metrics_df[col]

    return df


@dataclass
class EvaluationProgress:
    """Tracks evaluation progress and timing."""

    total_steps: int
    current_step: int = 0
    start_time: float = 0.0
    step_times: list = None
    total_errors: int = 0

    def __post_init__(self):
        self.step_times = []
        self.start_time = time.time()

    @staticmethod
    def format_time(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s"
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"

    def record_step(self, duration: float) -> None:
        self.step_times.append(duration)

    def increment(self) -> None:
        self.current_step += 1

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def eta(self) -> float | None:
        if not self.step_times:
            return None
        avg = sum(self.step_times) / len(self.step_times)
        return avg * (self.total_steps - self.current_step)

    @property
    def progress_pct(self) -> float:
        return self.current_step / self.total_steps if self.total_steps else 0


def _render_metric_summary(df: pd.DataFrame, metric_keys: list[str]) -> None:
    """Render summary metrics and chart for evaluations."""
    available = [m for m in metric_keys if m in df.columns]
    if not available:
        st.write(df.head(25))
        st.info("No metric scores available for the selected metrics.")
        return

    cols = st.columns(len(available))
    for idx, key in enumerate(available):
        label = key.replace("_", " ").title()
        cols[idx].metric(label, f"{df[key].mean():.3f}")

    chart_data = df[["input_query"] + available].melt(
        id_vars=["input_query"],
        value_vars=available,
        var_name="Metric",
        value_name="Score",
    )
    chart_data["Metric"] = chart_data["Metric"].str.replace("_", " ").str.title()

    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Metric:N", title="Metric"),
            y=alt.Y("mean(Score):Q", title="Average Score", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("Metric:N", legend=None),
            tooltip=["Metric", alt.Tooltip("mean(Score):Q", format=".3f", title="Avg Score")],
        )
        .properties(height=250, title="Average Scores by Metric")
    )
    st.altair_chart(chart, use_container_width=True)


@st.fragment
def _render_result_carousel(df: pd.DataFrame, metric_keys: list[str]) -> None:
    """Render evaluation results in a carousel format."""
    if df.empty:
        st.info("No evaluation results to display.")
        return

    labels = [f"{i + 1}: {row['input_query'][:40]}..." if len(str(row["input_query"])) > 40 else f"{i + 1}: {row['input_query']}" for i, row in df.iterrows()]
    idx = render_carousel_nav(len(df), "eval_carousel_index", labels, "Result")
    st.divider()

    row = df.iloc[idx]
    st.markdown(f"### {row['input_query']}")
    st.caption(f"Type: **{row.get('input_type', 'Unknown')}** | Model: **{row.get('evaluation_model', 'N/A')}** | Evaluated: {row.get('created_on', 'N/A')}")

    available = [m for m in metric_keys if m in df.columns and pd.notna(row.get(m))]
    if available:
        cols = st.columns(len(available))
        for i, key in enumerate(available):
            score = row[key]
            delta_color = "normal" if score >= 0.7 else ("inverse" if score < 0.4 else "off")
            cols[i].metric(key.replace("_", " ").title(), f"{score:.3f}", delta_color=delta_color)

    st.markdown("**Retrieved Context**")
    chunks = row.get("chunks", "")
    if len(chunks) > 500:
        with st.expander("View full context", expanded=False):
            st.text(chunks)
        st.info(chunks[:500] + "...")
    else:
        st.info(chunks)

    reasons = row.get("reasons") or {}
    if reasons and any(reasons.values()):
        st.divider()
        st.markdown("**Chain-of-Thought Reasoning**")
        for key in available:
            if data := reasons.get(key):
                with st.expander(f"{key.replace('_', ' ').title()} Reasoning"):
                    render_reasoning(data)


def run_evaluations(
    data_ops: SnowflakeDataOperations,
    queries: pd.DataFrame,
    model: str,
) -> None:
    """Run context_relevance evaluations on queries with progress tracking."""
    provider = Cortex(data_ops._session, model_engine=model)
    total_queries = len(queries)
    progress = EvaluationProgress(total_steps=total_queries)

    st.markdown("---")
    header_cols = st.columns([2, 1, 1, 1])
    with header_cols[0]:
        bar = st.progress(0, text="Initializing...")
    with header_cols[1]:
        elapsed_disp = st.empty()
        elapsed_disp.metric("Elapsed", "0s")
    with header_cols[2]:
        step_time_disp = st.empty()
        step_time_disp.metric("Step Time", "—")
    with header_cols[3]:
        eta_disp = st.empty()

    status_disp = st.empty()

    st.markdown("**Completed Evaluations**")
    table_disp = st.empty()
    results = []

    step_start_time = time.time()
    last_step_duration = None

    def update_progress_display(status: str, starting_new_step: bool = True):
        """Update progress bar, timers, and status."""
        nonlocal step_start_time, last_step_duration

        elapsed_disp.metric("Elapsed", progress.format_time(progress.elapsed))

        if starting_new_step:
            if last_step_duration is not None:
                step_time_disp.metric("Last Step", progress.format_time(last_step_duration))
            step_start_time = time.time()
        else:
            current_step_time = time.time() - step_start_time
            step_time_disp.metric("Step Time", progress.format_time(current_step_time))

        bar.progress(progress.progress_pct, text=f"Step {progress.current_step}/{progress.total_steps}")

        if progress.eta is not None:
            eta_disp.metric("ETA", progress.format_time(progress.eta))

        status_disp.info(f"⏳ **{status}**")

    def update_table():
        if results:
            df = pd.DataFrame(results)
            table_disp.dataframe(df, use_container_width=True, hide_index=True)

    for q_idx, (_, row) in enumerate(queries.iterrows(), 1):
        step_start = time.time()
        search_id = int(row["SEARCH_ID"])
        query_text = row["INPUT_QUERY"]
        chunks = row["CHUNK_TEXT"]
        short_query = query_text[:60] + "..." if len(query_text) > 60 else query_text

        result_row = {"Query": short_query, "Status": "Evaluating..."}
        results.append(result_row)
        update_table()

        progress.increment()
        update_progress_display(f"Query {q_idx}/{total_queries}: Evaluating context relevance...")

        eval_data = pd.Series({"query": query_text, "context": truncate_context(chunks)})
        score, reasons, error = evaluate_metric(provider, "Context Relevance", eval_data)

        last_step_duration = time.time() - step_start

        if error:
            result_row["Context Relevance"] = "Error"
            evaluation = {"context_relevance": {"score": None, "reasons": {"error": error}}}
            progress.total_errors += 1
        else:
            result_row["Context Relevance"] = f"{score:.3f}"
            evaluation = {"context_relevance": {"score": score, "reasons": reasons or {}}}

        progress.record_step(last_step_duration)

        result_row["Status"] = "Saving..."
        update_table()

        try:
            data_ops.save_evaluation_results(
                search_id=search_id,
                input_query=query_text,
                chunks=chunks,
                evaluation_model=model,
                evaluation=evaluation,
            )
            result_row["Status"] = "Complete"
        except Exception as e:
            st.warning(f"Could not save result for search_id {search_id}: {e}")
            result_row["Status"] = "Save failed"

        update_table()

    total_elapsed = progress.elapsed
    bar.progress(1.0, text="Complete!")
    elapsed_disp.metric("Total Time", progress.format_time(total_elapsed))
    step_time_disp.empty()
    eta_disp.empty()
    status_disp.empty()

    avg = total_elapsed / total_queries if total_queries else 0
    if progress.total_errors:
        st.warning(f"Completed with {progress.total_errors} error(s). Processed {total_queries} queries in {progress.format_time(total_elapsed)} ({progress.format_time(avg)}/query avg). Try a different model if errors persist.")
    else:
        st.success(f"Evaluation complete! Processed {total_queries} queries in {progress.format_time(total_elapsed)} ({progress.format_time(avg)}/query avg)")


def _render_completion_stats(stats: dict) -> None:
    """Render evaluation completion metrics."""
    if not stats:
        return

    st.subheader("Evaluation Progress")
    cols = st.columns(len(stats))
    for idx, (input_type, data) in enumerate(stats.items()):
        total, evaluated = data["total"], data["evaluated"]
        pct = (evaluated / total * 100) if total else 0
        with cols[idx]:
            st.metric(
                label=input_type.replace("_", " ").title(),
                value=f"{evaluated}/{total}",
                delta=f"{pct:.3f}% complete",
                delta_color="normal" if pct < 100 else "off",
            )
    st.divider()


def _render_model_selector() -> str:
    """Render model selection UI and return selected model."""
    col_model, col_help = st.columns([1, 2])
    with col_model:
        model = st.selectbox(
            "Evaluation Model",
            options=EVALUATION_MODELS,
            index=0,
            key="evaluation_model_select",
            help="Select the model for LLM-as-a-Judge evaluations",
        )
    with col_help:
        st.caption("This model acts as an LLM-as-a-Judge, scoring each search result using TruLens evaluation metrics. Larger models generally provide more accurate and consistent quality assessments.")
    return model


@st.fragment
def _render_run_section(data_ops: SnowflakeDataOperations, all_results: pd.DataFrame, model: str, expanded: bool) -> None:
    """Render the run evaluations section as a fragment to isolate progress UI."""
    with st.expander("Run New Evaluations", expanded=expanded):
        st.warning("⚠️ Running evaluations from the app is temporarily disabled. Please use the batch evaluation scripts instead.")
        st.markdown("Select which queries to evaluate:")
        metrics = st.multiselect(
            "Evaluation Metrics",
            options=METRIC_OPTIONS,
            default=["Context Relevance"],
            key="eval_metrics_run",
            disabled=True,
        )
        available_types = []
        if not all_results.empty and "INPUT_TYPE" in all_results.columns:
            available_types = all_results["INPUT_TYPE"].dropna().unique().tolist()
        mode = st.radio(
            "Selection Mode",
            options=["By Query Type", "Specific Queries"],
            horizontal=True,
            key="eval_selection_mode",
            disabled=True,
        )
        queries = pd.DataFrame()

        if mode == "By Query Type":
            col1, col2 = st.columns([2, 1])
            with col1:
                types = st.multiselect(
                    "Query Types to Evaluate",
                    options=available_types,
                    default=[],
                    key="eval_types_to_run",
                    disabled=True,
                )
            with col2:
                skip = st.checkbox("Skip already evaluated", value=True, key="skip_evaluated", disabled=True)

            if types and not all_results.empty:
                queries = all_results[all_results["INPUT_TYPE"].isin(types)]
                if skip:
                    queries = queries[~queries["EVALUATED"]]
        else:
            if not all_results.empty:
                options = [(row["SEARCH_ID"], f"{'✓' if row['EVALUATED'] else '○'} [{row['INPUT_TYPE']}] {row['INPUT_QUERY'][:60]}...") for _, row in all_results.iterrows()]
                selected = st.multiselect(
                    "Select Queries to Evaluate",
                    options=[o[0] for o in options],
                    format_func=lambda x: next((o[1] for o in options if o[0] == x), str(x)),
                    key="eval_specific_queries",
                    help="✓ = already evaluated, ○ = not evaluated",
                    disabled=True,
                )
                if selected:
                    queries = all_results[all_results["SEARCH_ID"].isin(selected)]

        if queries.empty:
            st.caption("Select query types or specific queries to evaluate.")
            return

        unevaluated = (~queries["EVALUATED"]).sum()
        re_evaluated = queries["EVALUATED"].sum()
        num_metrics = len(metrics) if metrics else 1

        est_secs = 20 * (num_metrics + 1) * len(queries)
        est_mins = est_secs / 60

        col1, col2 = st.columns([2, 1])
        with col1:
            st.info(f"**{len(queries)}** queries selected: {unevaluated} new, {re_evaluated} will be re-evaluated")
        with col2:
            st.caption(f"Estimated time: ~{est_secs:.0f}s" if est_mins < 1 else f"Estimated time: ~{est_mins:.0f}min")

        st.button("Run Evaluation", key="run_eval_btn", type="primary", disabled=True)


def _render_results_section(existing_results: pd.DataFrame) -> None:
    """Render the evaluation results section."""
    st.subheader("Evaluation Results")

    col1, col2 = st.columns(2)
    with col1:
        view_metrics = st.multiselect(
            "Metrics to Display",
            options=METRIC_OPTIONS,
            default=["Context Relevance"],
            key="eval_metrics_view",
        )

    result_types = existing_results["INPUT_TYPE"].dropna().unique().tolist() if "INPUT_TYPE" in existing_results.columns else []
    with col2:
        view_types = st.multiselect(
            "Filter by Query Type",
            options=result_types,
            default=result_types,
            key="eval_types_view",
        )

    df = parse_evaluation_data(existing_results)
    if view_types and "input_type" in df.columns:
        df = df[df["input_type"].isin(view_types)]

    if df.empty:
        st.info("No evaluation results match the selected filters.")
        return

    metric_keys = [to_metric_key(m) for m in view_metrics]
    _render_metric_summary(df, metric_keys)
    st.divider()
    st.markdown("**Detailed Results**")
    _render_result_carousel(df.reset_index(drop=True), metric_keys)


def render_evaluation_tab(data_ops: SnowflakeDataOperations) -> None:
    """Main entry point for the Evaluation tab."""
    st.header("LLM-as-a-Judge Evaluation")
    st.caption("Evaluate search results using TruLens metrics powered by Cortex LLMs.")

    completion_stats = data_ops.get_evaluation_completion_stats()
    all_results = data_ops.extract_search_results_for_evaluation()
    existing = data_ops.get_evaluation_results()

    _render_completion_stats(completion_stats)
    model = _render_model_selector()

    try:
        evaluated_ids = set(existing["SEARCH_ID"].tolist()) if not existing.empty else set()

        if not all_results.empty:
            all_results["EVALUATED"] = all_results["SEARCH_ID"].isin(evaluated_ids)

        _render_run_section(data_ops, all_results, model, expanded=not evaluated_ids)

        if not existing.empty:
            _render_results_section(existing)
        else:
            st.info("No evaluation results yet. Use the section above to run evaluations.")

    except Exception as e:
        st.error(f"Error running evaluation: {e}")
        st.info("Make sure TruLens and the Cortex provider are properly configured.")
