import os
import zipfile
from pathlib import Path

import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session

from app.data_operations import SnowflakeDataOperations
from app.ui_components import (
    render_eda_tab,
    render_evaluation_tab,
    render_feedback_tab,
    render_playground_tab,
)
from config import ui_config

NLTK_DATA_PATH = Path(os.path.dirname(__file__)) / "nltk_data"
TOKENIZER_PATH = NLTK_DATA_PATH / "tokenizers"

try:
    import nltk

    os.environ["NLTK_DATA"] = str(NLTK_DATA_PATH)
    nltk.data.path.insert(0, str(NLTK_DATA_PATH))

    if not (TOKENIZER_PATH / "punkt_tab").exists():
        TOKENIZER_PATH.mkdir(parents=True, exist_ok=True)
        app_dir = Path(os.path.dirname(__file__))
        for zip_name in ("punkt.zip", "punkt_tab.zip"):
            zip_path = app_dir / zip_name
            if zip_path.exists():
                with zipfile.ZipFile(zip_path, mode="r") as zf:
                    zf.extractall(TOKENIZER_PATH)
except Exception:
    pass


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
