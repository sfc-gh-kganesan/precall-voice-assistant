import streamlit as st
from config import db_config, ui_config

st.set_page_config(
    page_title=ui_config.page_title,
    page_icon=ui_config.page_icon,
    layout="wide",
)

from data_operations import SnowflakeDataOperations  # noqa: E402
from eda import render_eda_tab  # noqa: E402
from evaluation import render_evaluation_tab  # noqa: E402
from seeding import get_sync_status, sync_searches  # noqa: E402
from snowflake.snowpark.context import get_active_session  # noqa: E402
from taxonomy import render_taxonomy_tab  # noqa: E402
from ui_components import render_feedback_tab, render_playground_tab  # noqa: E402


@st.cache_resource
def get_session():
    return get_active_session()


@st.cache_resource
def get_data_operations():
    session = get_session()
    return SnowflakeDataOperations(session)


def render_header_metrics(data_ops: SnowflakeDataOperations) -> None:
    """Render prominent dashboard metrics at the top of the app."""
    stats = data_ops.get_dashboard_stats()

    eval_pct = stats["eval_pct"]
    st.metric(
        "Evaluation Progress",
        f"{stats['eval_completed']}/{stats['eval_total']}",
        delta=f"{eval_pct:.3f}% complete",
        delta_color="normal" if eval_pct < 100 else "off",
    )


def main() -> None:
    st.title(ui_config.page_title)
    st.markdown("Evaluate and improve your Cortex Search retrieval quality through human feedback, LLM-as-a-judge metrics, and taxonomy analysis.")
    st.caption(f"Connected to `{db_config.database}.{db_config.schema}` | Search Service: `{db_config.search_service}`")

    session = get_session()
    data_ops = get_data_operations()

    with st.sidebar:
        st.image("sanofi-600px.jpg")
        st.header("Search Status")
        sync_status = get_sync_status(session)
        unsearched_golden = sync_status["unsearched_golden_pairs"]
        unsearched_synthetic = sync_status["unsearched_synthetic_pairs"]
        total_golden = sync_status["total_golden_pairs"]
        total_synthetic = sync_status["total_synthetic_pairs"]
        total_adhoc = sync_status["total_adhoc_queries"]

        st.subheader("Totals")
        col1, col2, col3 = st.columns(3)
        col1.metric("Golden", total_golden)
        col2.metric("Synthetic", total_synthetic)
        col3.metric("Adhoc", total_adhoc)

        st.subheader("Pending Sync")
        col1, col2 = st.columns(2)
        col1.metric("Golden", unsearched_golden)
        col2.metric("Synthetic", unsearched_synthetic)

        if unsearched_golden > 0 or unsearched_synthetic > 0:
            sync_golden = st.checkbox("Sync Golden Pairs", value=unsearched_golden > 0, disabled=unsearched_golden == 0)
            sync_synthetic = st.checkbox("Sync Synthetic Pairs", value=unsearched_synthetic > 0, disabled=unsearched_synthetic == 0)

            if st.button("Sync Now", type="primary"):
                with st.spinner("Syncing searches..."):
                    results = sync_searches(session, data_ops, sync_golden=sync_golden, sync_synthetic=sync_synthetic)
                    st.success(f"Synced {results['golden_pairs']} golden pairs and {results['synthetic_pairs']} synthetic pairs")
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

    render_header_metrics(data_ops)
    st.divider()

    input_types = data_ops.get_input_types()

    def load_results_by_type(_data_ops, result_type):
        return _data_ops.extract_search_results(result_type, ["SEARCH_ID"])

    tab_coverage, tab_eval, tab_playground, tab_feedback, tab_eda = st.tabs(["Quality Coverage", "Evaluation", "Playground", "Feedback", "EDA"])

    with tab_coverage:
        render_taxonomy_tab(get_session())

    with tab_eval:
        render_evaluation_tab(data_ops)

    with tab_playground:
        render_playground_tab(data_ops)

    with tab_feedback:
        render_feedback_tab(data_ops, input_types, load_results_by_type)

    with tab_eda:
        render_eda_tab(data_ops)


main()
