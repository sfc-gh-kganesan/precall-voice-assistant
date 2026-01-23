from collections.abc import Callable
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st


def to_metric_key(metric: str) -> str:
    return metric.lower().replace(" ", "_")


def render_carousel_nav(
    total_items: int,
    session_key: str,
    item_labels: list[str] = None,
    label_prefix: str = "Item",
    on_change: Callable[[int], Any] = None,
) -> int:
    """Render a reusable carousel navigation with prev/next buttons and jump-to selector.

    Args:
        total_items: Total number of items in the carousel
        session_key: Unique session state key for tracking the current index
        item_labels: Optional list of labels for the jump-to selector
        label_prefix: Prefix for the counter display (e.g., "Query", "Result")
        on_change: Optional callback when index changes

    Returns:
        The current index (0-based)
    """
    if total_items == 0:
        return 0

    if session_key not in st.session_state:
        st.session_state[session_key] = 0

    st.session_state[session_key] = min(st.session_state[session_key], total_items - 1)
    current_idx = st.session_state[session_key]

    col1, col2, col3, col4 = st.columns([1, 1, 2, 4])

    with col1:
        if st.button("← Previous", disabled=current_idx == 0, use_container_width=True, key=f"{session_key}_prev"):
            st.session_state[session_key] -= 1
            if on_change:
                on_change(st.session_state[session_key])

    with col2:
        if st.button("Next →", disabled=current_idx >= total_items - 1, use_container_width=True, key=f"{session_key}_next"):
            st.session_state[session_key] += 1
            if on_change:
                on_change(st.session_state[session_key])

    current_idx = st.session_state[session_key]

    with col3:
        st.container(height=42, border=False).markdown(f"**{label_prefix} {current_idx + 1} of {total_items}**")

    with col4:
        if item_labels and len(item_labels) == total_items:
            labels = item_labels
        else:
            labels = [f"{i + 1}" for i in range(total_items)]

        selected = st.selectbox(
            "Jump to",
            range(total_items),
            index=current_idx,
            format_func=lambda x: labels[x],
            key=f"{session_key}_jump",
            label_visibility="collapsed",
        )
        if selected != current_idx:
            st.session_state[session_key] = selected
            if on_change:
                on_change(selected)

    return st.session_state[session_key]


def create_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    tooltip_cols: list[str],
    x_title: str = None,
    y_title: str = None,
    y_scale: alt.Scale = None,
    height: int = None,
) -> alt.Chart:
    x_encoding = alt.X(f"{x_col}:Q" if ":" not in x_col else x_col, title=x_title or x_col)
    y_encoding = alt.Y(
        f"{y_col}:N" if ":" not in y_col else y_col,
        title=y_title or y_col,
        sort="-x" if y_scale is None else None,
        scale=y_scale,
    )
    chart = alt.Chart(df).mark_bar().encode(x=x_encoding, y=y_encoding, tooltip=tooltip_cols).properties(title=title)
    if height:
        chart = chart.properties(height=height)
    return chart


def render_stars(rating: int) -> str:
    return "★" * rating + "☆" * (5 - rating)


def render_reasoning(reasons: dict) -> None:
    if isinstance(reasons, dict) and reasons:
        if "reasons" in reasons:
            st.markdown(f"*Reasoning:* {reasons['reasons']}")
        elif "reason" in reasons:
            st.markdown(f"*Reasoning:* {reasons['reason']}")
        else:
            st.json(reasons)
