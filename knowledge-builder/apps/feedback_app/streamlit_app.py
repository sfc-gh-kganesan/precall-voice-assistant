import streamlit as st
from config import config

st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout="wide",
)

from components import render_feedback_tab, render_playground_tab  # noqa: E402
from store import InitializeFiltersAction, SetInputTypeAction, dispatch, get_store, init_store  # noqa: E402

from data import get_feedback_counts, get_input_types, get_search_results, get_session, get_sync_status  # noqa: E402


def render_sidebar() -> None:
    """Render sidebar with search status."""
    with st.sidebar:
        st.header("Search Status")
        session = get_session()
        sync_status = get_sync_status(session)

        col1, col2, col3 = st.columns(3)
        col1.metric("Golden", sync_status["total_golden_pairs"])
        col2.metric("Synthetic", sync_status["total_synthetic_pairs"])
        col3.metric("Adhoc", sync_status["total_adhoc_queries"])


def main() -> None:
    st.title(config.PAGE_TITLE)
    st.markdown("Provide feedback on Cortex Search retrieval quality.")
    st.caption(f"Connected to `{config.DATABASE}.{config.SCHEMA}` | Search Service: `{config.SEARCH_SERVICE}`")

    # Initialize state
    init_store()
    session = get_session()

    # Sidebar
    render_sidebar()

    # Get available input types for filtering
    input_types = get_input_types(session)

    # Initialize filters on first load
    store = get_store()
    if not store.filters_initialized and input_types:
        dispatch(InitializeFiltersAction(default_input_type=input_types[0]))

    # Tabs
    tab_playground, tab_feedback = st.tabs(["Playground", "Feedback"])

    with tab_playground:
        render_playground_tab(session)

    with tab_feedback:
        # Input type filter
        selected_type = st.selectbox(
            "Query Type",
            options=input_types,
            index=input_types.index(store.selected_input_type) if store.selected_input_type in input_types else 0,
            key="input_type_selector",
        )

        if selected_type != store.selected_input_type:
            dispatch(SetInputTypeAction(input_type=selected_type))
            st.rerun()

        # Load data for selected type
        if selected_type:
            source_df = get_search_results(session, selected_type)
            feedback_counts = get_feedback_counts(session)
            render_feedback_tab(session, source_df, feedback_counts)
        else:
            st.info("Select a query type to review results.")


main()
