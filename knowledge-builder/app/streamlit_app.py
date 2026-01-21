import streamlit as st
from config import db_config, ui_config

st.set_page_config(
    page_title=ui_config.page_title,
    page_icon=ui_config.page_icon,
    layout="wide",
)

import pandas as pd  # noqa: E402
from data_operations import SnowflakeDataOperations  # noqa: E402
from eda import render_eda_tab  # noqa: E402
from evaluation import render_evaluation_tab  # noqa: E402
from seeding import get_sync_status, sync_searches  # noqa: E402
from snowflake.snowpark import Session  # noqa: E402
from snowflake.snowpark.context import get_active_session  # noqa: E402
from ui_components import render_feedback_tab, render_playground_tab  # noqa: E402


@st.cache_resource
def get_session():
    try:
        return get_active_session()
    except Exception:
        return Session.builder.config("connection_name", "aifde").create()


@st.cache_resource
def get_data_operations():
    session = get_session()
    return SnowflakeDataOperations(session)


@st.cache_data(ttl=300)
def load_baseline_results(_data_ops: SnowflakeDataOperations):
    return _data_ops.get_baseline_results()


@st.cache_data(ttl=300)
def load_adhoc_results(_data_ops: SnowflakeDataOperations):
    return _data_ops.get_adhoc_results()


def render_header_metrics(data_ops: SnowflakeDataOperations, baseline_df: pd.DataFrame, adhoc_df: pd.DataFrame) -> None:
    feedback_counts = data_ops.get_feedback_counts()
    total_feedback = int(feedback_counts["FEEDBACK_COUNT"].sum()) if not feedback_counts.empty else 0
    total_queries = baseline_df["INPUT_QUERY"].nunique() if not baseline_df.empty else 0
    total_adhoc = adhoc_df["INPUT_QUERY"].nunique() if not adhoc_df.empty else 0
    synthetic_count = data_ops.get_synthetic_query_count()
    avg_similarity = baseline_df["COSINE_SIMILARITY"].mean() if not baseline_df.empty else 0

    cols = st.columns(5)
    cols[0].metric("Golden Pairs", total_queries)
    cols[1].metric("Ad-hoc Searches", total_adhoc)
    cols[2].metric("Synthetic Queries", synthetic_count)
    cols[3].metric("Feedback Received", total_feedback)
    cols[4].metric("Avg Similarity", f"{avg_similarity:.3f}")


def main() -> None:
    st.title(ui_config.page_title)
    st.caption(f"Connected to `{db_config.database}.{db_config.schema}` | Search Service: `{db_config.search_service}`")

    session = get_session()
    data_ops = get_data_operations()

    with st.sidebar:
        st.header("Sync Searches")
        sync_status = get_sync_status(session)
        unsearched_golden = sync_status["unsearched_golden_pairs"]
        unsearched_synthetic = sync_status["unsearched_synthetic_pairs"]

        st.metric("Unsearched Golden Pairs", unsearched_golden)
        st.metric("Unsearched Synthetic Pairs", unsearched_synthetic)

        if unsearched_golden > 0 or unsearched_synthetic > 0:
            sync_golden = st.checkbox("Sync Golden Pairs", value=unsearched_golden > 0, disabled=unsearched_golden == 0)
            sync_synthetic = st.checkbox("Sync Synthetic Pairs", value=unsearched_synthetic > 0, disabled=unsearched_synthetic == 0)

            if st.button("Sync Now", type="primary"):
                with st.spinner("Syncing searches..."):
                    results = sync_searches(session, data_ops, sync_golden=sync_golden, sync_synthetic=sync_synthetic)
                    st.success(f"Synced {results['golden_pairs']} golden pairs and {results['synthetic_pairs']} synthetic pairs")
                    load_baseline_results.clear()
                    load_adhoc_results.clear()
                    st.rerun()
        else:
            st.info("All pairs are synced.")

    is_valid, missing_resources = data_ops.validate_environment()
    if not is_valid:
        st.error("Missing required resources:")
        for resource in missing_resources:
            st.error(f"  - {resource}")
        st.info("Please ensure all required tables and services exist before using this application.")
        st.stop()

    baseline_results_df = load_baseline_results(data_ops)
    adhoc_results_df = load_adhoc_results(data_ops)

    render_header_metrics(data_ops, baseline_results_df, adhoc_results_df)
    st.divider()

    if baseline_results_df.empty and adhoc_results_df.empty:
        st.warning("No results data available.")

    input_types = []
    if not baseline_results_df.empty:
        input_types.append("baseline")
    if not adhoc_results_df.empty:
        input_types.append("adhoc")

    def load_results_by_type(_data_ops, result_type):
        if result_type == "baseline":
            return baseline_results_df
        elif result_type == "adhoc":
            return adhoc_results_df
        return _data_ops.get_baseline_results().head(0)

    tabs = ["Feedback", "Playground", "Evaluation", "EDA"]

    if "selected_tab" not in st.session_state or st.session_state.selected_tab not in tabs:
        st.session_state.selected_tab = "Feedback"

    selected_tab = st.radio(
        "Navigation",
        tabs,
        index=tabs.index(st.session_state.selected_tab),
        key="tab_selector",
        horizontal=True,
        label_visibility="collapsed",
    )

    st.session_state.selected_tab = selected_tab

    st.divider()

    def clear_results_cache():
        load_baseline_results.clear()
        load_adhoc_results.clear()

    if selected_tab == "Feedback":
        render_feedback_tab(data_ops, input_types, load_results_by_type, on_feedback_submit=clear_results_cache)
    elif selected_tab == "Playground":
        render_playground_tab(data_ops)
    elif selected_tab == "Evaluation":
        render_evaluation_tab(data_ops)
    elif selected_tab == "EDA":
        render_eda_tab(data_ops)


main()
