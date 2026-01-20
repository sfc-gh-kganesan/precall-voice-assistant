import altair as alt
import pandas as pd
import streamlit as st


def to_metric_key(metric: str) -> str:
    return metric.lower().replace(" ", "_")


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
