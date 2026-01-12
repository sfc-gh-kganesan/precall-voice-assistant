import streamlit as st
from data_operations import SnowflakeDataOperations
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
from ui_components import (
    render_eda_tab,
    render_evaluation_tab,
    render_feedback_tab,
    render_playground_tab,
)

from config import ui_config


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


def main() -> None:
    st.title(ui_config.page_title)

    data_ops = get_data_operations()

    is_valid, missing_resources = data_ops.validate_environment()
    if not is_valid:
        st.error("Missing required resources:")
        for resource in missing_resources:
            st.error(f"  - {resource}")
        st.info("Please ensure all required tables and services exist before using this application.")
        st.stop()

    baseline_results_df = load_baseline_results(data_ops)
    adhoc_results_df = load_adhoc_results(data_ops)

    if baseline_results_df.empty and adhoc_results_df.empty:
        st.warning("No results data available.")
        st.stop()

    if "selected_tab" not in st.session_state:
        st.session_state.selected_tab = "Feedback"

    selected_tab = st.radio(
        "Navigation",
        ["Feedback", "Playground", "Evaluation", "EDA"],
        index=["Feedback", "Playground", "Evaluation", "EDA"].index(st.session_state.selected_tab),
        key="tab_selector",
        horizontal=True,
        label_visibility="collapsed",
    )

    st.session_state.selected_tab = selected_tab

    st.divider()

    if selected_tab == "Feedback":
        render_feedback_tab(data_ops, baseline_results_df, adhoc_results_df)
    elif selected_tab == "Playground":
        render_playground_tab(data_ops)
    elif selected_tab == "Evaluation":
        render_evaluation_tab(data_ops)
    elif selected_tab == "EDA":
        render_eda_tab(data_ops)


main()
