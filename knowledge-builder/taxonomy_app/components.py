"""
UI components for the Sunburst Push-Down Taxonomy application.
Each component is a pure function that renders UI based on state.
"""

import json

import pandas as pd
import plotly.express as px
import streamlit as st
from store import (
    ClearSelectionAction,
    SetAnswerableFilterAction,
    SetBackfillableFilterAction,
    SetResolutionFilterAction,
    SetSelectedPathAction,
    SetSourceTypesAction,
    dispatch,
    get_store,
)


@st.fragment
def render_sunburst(grouped_df: pd.DataFrame, path_cols: list[str]) -> None:
    """
    Render the interactive sunburst chart (visualization only).
    Selection is handled by separate breadcrumb controls.
    """
    if grouped_df.empty:
        st.warning("No data available for sunburst visualization.")
        return

    # Create sunburst with custom purple gradient (white to dark purple = better relevance)
    purple_gradient = ["#FFFFFF", "#E5CCFA", "#CB99F5", "#B066F0", "#9533EB", "#7A00E6"]
    fig = px.sunburst(
        grouped_df,
        path=path_cols,
        values="TICKET_COUNT",
        color="CONTEXT_RELEVANCE_SCORE",
        color_continuous_scale=purple_gradient,
        title="Taxonomy Distribution by Ticket Count",
    )

    fig.update_traces(hovertemplate=("<b>%{label}</b><br>%{id}<br>Ticket Count: %{value}<br>Context Relevance: %{color:.3f}<extra></extra>"))

    fig.update_layout(
        height=600,
        margin={"t": 50, "l": 0, "r": 0, "b": 0},
        coloraxis_colorbar_title="Context Relevance Score",
    )

    # Render chart (visualization only, no click handling)
    st.plotly_chart(fig, use_container_width=True, key="sunburst_chart")


def render_taxonomy_selector(df: pd.DataFrame) -> None:
    """
    Render cascading dropdowns for taxonomy level selection.
    Each level filters the options available in the next level.
    """
    store = get_store()

    # Handle clear request from previous run (must happen before widgets are instantiated)
    if st.session_state.get("_clear_taxonomy_requested"):
        del st.session_state["_clear_taxonomy_requested"]
        # Set widget values to "All" before widgets are created
        st.session_state["sel_l1"] = "All"
        st.session_state["sel_l2"] = "All"
        st.session_state["sel_l3"] = "All"
        st.session_state["sel_l4"] = "All"

    col1, col2, col3, col4, col_clear = st.columns([2, 2, 2, 2, 1])

    # L1 selector
    with col1:
        l1_options = ["All"] + sorted(df["L1_TAG"].dropna().unique().tolist())
        l1_default = store.selected_l1 if store.selected_l1 in l1_options else "All"
        l1_index = l1_options.index(l1_default) if l1_default in l1_options else 0

        st.selectbox(
            "Level 1",
            options=l1_options,
            index=l1_index,
            key="sel_l1",
            on_change=lambda: dispatch(
                SetSelectedPathAction(
                    l1=st.session_state.sel_l1 if st.session_state.sel_l1 != "All" else None,
                    l2=None,
                    l3=None,
                    l4=None,  # Reset children on parent change
                )
            ),
        )

    # L2 selector - filtered by L1
    with col2:
        if store.selected_l1:
            l2_df = df[df["L1_TAG"] == store.selected_l1]
        else:
            l2_df = df
        l2_options = ["All"] + sorted(l2_df["L2_TAG"].dropna().unique().tolist())
        l2_default = store.selected_l2 if store.selected_l2 in l2_options else "All"
        l2_index = l2_options.index(l2_default) if l2_default in l2_options else 0

        st.selectbox(
            "Level 2",
            options=l2_options,
            index=l2_index,
            key="sel_l2",
            disabled=not store.selected_l1,
            on_change=lambda: dispatch(
                SetSelectedPathAction(
                    l1=store.selected_l1,
                    l2=st.session_state.sel_l2 if st.session_state.sel_l2 != "All" else None,
                    l3=None,
                    l4=None,  # Reset children
                )
            ),
        )

    # L3 selector - filtered by L1 + L2
    with col3:
        if store.selected_l1 and store.selected_l2:
            l3_df = df[(df["L1_TAG"] == store.selected_l1) & (df["L2_TAG"] == store.selected_l2)]
        else:
            l3_df = pd.DataFrame()
        l3_options = ["All"] + sorted(l3_df["L3_TAG"].dropna().unique().tolist()) if not l3_df.empty else ["All"]
        l3_default = store.selected_l3 if store.selected_l3 in l3_options else "All"
        l3_index = l3_options.index(l3_default) if l3_default in l3_options else 0

        st.selectbox(
            "Level 3",
            options=l3_options,
            index=l3_index,
            key="sel_l3",
            disabled=not store.selected_l2,
            on_change=lambda: dispatch(
                SetSelectedPathAction(
                    l1=store.selected_l1,
                    l2=store.selected_l2,
                    l3=st.session_state.sel_l3 if st.session_state.sel_l3 != "All" else None,
                    l4=None,  # Reset child
                )
            ),
        )

    # L4 selector - filtered by L1 + L2 + L3
    with col4:
        if store.selected_l1 and store.selected_l2 and store.selected_l3:
            l4_df = df[(df["L1_TAG"] == store.selected_l1) & (df["L2_TAG"] == store.selected_l2) & (df["L3_TAG"] == store.selected_l3)]
        else:
            l4_df = pd.DataFrame()
        l4_options = ["All"] + sorted(l4_df["L4_TAG"].dropna().unique().tolist()) if not l4_df.empty else ["All"]
        l4_default = store.selected_l4 if store.selected_l4 in l4_options else "All"
        l4_index = l4_options.index(l4_default) if l4_default in l4_options else 0

        st.selectbox(
            "Level 4",
            options=l4_options,
            index=l4_index,
            key="sel_l4",
            disabled=not store.selected_l3,
            on_change=lambda: dispatch(
                SetSelectedPathAction(
                    l1=store.selected_l1,
                    l2=store.selected_l2,
                    l3=store.selected_l3,
                    l4=st.session_state.sel_l4 if st.session_state.sel_l4 != "All" else None,
                )
            ),
        )

    # Clear button
    with col_clear:
        st.markdown("<br>", unsafe_allow_html=True)  # Align with dropdowns
        if st.button("Clear", key="btn_clear_taxonomy"):
            dispatch(ClearSelectionAction())
            # Set flag to clear widget keys on next run (before widgets are instantiated)
            st.session_state["_clear_taxonomy_requested"] = True
            st.rerun()

    # Show current selection as breadcrumb
    selection_parts = []
    if store.selected_l1:
        selection_parts.append(store.selected_l1)
    if store.selected_l2:
        selection_parts.append(store.selected_l2)
    if store.selected_l3:
        selection_parts.append(store.selected_l3)
    if store.selected_l4:
        selection_parts.append(store.selected_l4)

    if selection_parts:
        st.caption(f"📍 {' > '.join(selection_parts)}")


def render_filters(source_types: list[str], answerable_options: list[str], resolution_options: list[str], backfillable_options: list[str]) -> None:
    """Render filter controls for source type, answerable_with_kb, resolution status, and backfillable."""
    store = get_store()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Use store values only if they're valid options, otherwise use all options
        source_default = [s for s in store.source_types if s in source_types]
        if not source_default:
            source_default = source_types

        st.multiselect("Source Type", options=source_types, default=source_default, key="ms_source_types", on_change=lambda: dispatch(SetSourceTypesAction(source_types=st.session_state.ms_source_types)))

    with col2:
        # Use store values only if they're valid options, otherwise use all options
        answerable_default = [a for a in store.answerable_filter if a in answerable_options]
        if not answerable_default:
            answerable_default = answerable_options

        st.multiselect("Self Serve Candidate", options=answerable_options, default=answerable_default, key="ms_answerable", on_change=lambda: dispatch(SetAnswerableFilterAction(values=st.session_state.ms_answerable)))

    with col3:
        # Use store values only if they're valid options, otherwise use all options
        resolution_default = [r for r in store.resolution_filter if r in resolution_options]
        if not resolution_default:
            resolution_default = resolution_options

        st.multiselect("Resolution Status", options=resolution_options, default=resolution_default, key="ms_resolution", on_change=lambda: dispatch(SetResolutionFilterAction(values=st.session_state.ms_resolution)))

    with col4:
        # Use store values only if they're valid options, otherwise use all options
        backfillable_default = [b for b in store.backfillable_filter if b in backfillable_options]
        if not backfillable_default:
            backfillable_default = backfillable_options

        st.multiselect("Backfillable", options=backfillable_options, default=backfillable_default, key="ms_backfillable", on_change=lambda: dispatch(SetBackfillableFilterAction(values=st.session_state.ms_backfillable)))


def inject_app_styles() -> None:
    """
    Inject application CSS styles from external file.
    Call once at the top of the main app, before any UI rendering.
    Uses CSS variables for theme-aware colors (light/dark mode support).
    """
    from pathlib import Path

    css_path = Path(__file__).parent / "styles.css"
    css = css_path.read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _bento_box_html(label: str, value: str, subtitle: str | None = None, small_value: bool = False) -> str:
    """
    Generate HTML for a single bento box.
    Returns HTML string to be combined with other boxes in a grid container.
    """
    value_class = "bento-value-small" if small_value else "bento-value"
    subtitle_html = f'<div class="bento-subtitle">{subtitle}</div>' if subtitle else ""

    return f'<div class="bento-box"><div class="bento-label">{label}</div><div class="{value_class}">{value}</div>{subtitle_html}</div>'


def render_kpi_bento(kpis: dict, resolution_filter: list[str] | None = None, backfillable_filter: list[str] | None = None) -> None:
    """Render KPI metrics as bento box cards using pure HTML flexbox."""

    # Determine if we should show the unresolved bento
    # Hide if resolution filter has only one value selected (trivially 100% or 0%)
    show_unresolved_bento = resolution_filter is None or len(resolution_filter) != 1

    # Determine if we should show the backfillable bento
    # Hide if backfillable filter has only one value selected (trivially 100% or 0%)
    show_backfillable_bento = backfillable_filter is None or len(backfillable_filter) != 1

    # Answerable breakdown (only show if multiple values)
    breakdown = kpis.get("answerable_breakdown", {})
    show_answerable_breakdown = len(breakdown) > 1

    # Build all bento box HTML
    boxes_html = []

    # Ticket Count
    ticket_count = kpis["ticket_count"]
    total_population = kpis.get("total_population", ticket_count)
    ticket_pct = kpis.get("ticket_pct_of_total", 100.0)
    boxes_html.append(_bento_box_html(label="Ticket Count", value=f"{ticket_count:,}", subtitle=f"({ticket_pct:.1f}% of {total_population:,} total)"))

    # Avg Context Relevance
    relevance = kpis["avg_context_relevance"]
    relevance_display = f"{relevance:.2f}" if relevance is not None and not pd.isna(relevance) else "N/A"
    boxes_html.append(_bento_box_html(label="Avg Context Relevance", value=relevance_display))

    # Coverage (context relevance >= 0.8)
    coverage_count = kpis.get("coverage_count", 0)
    coverage_pct = kpis.get("coverage_pct", 0.0)
    boxes_html.append(_bento_box_html(label="Coverage", value=f"{coverage_pct:.1f}%", subtitle=f"{coverage_count:,} with CR ≥ 0.8"))

    # Backfillable (conditional) - incidents only
    if show_backfillable_bento:
        backfillable_count = kpis.get("backfillable_count", 0)
        backfillable_pct = kpis.get("backfillable_pct", 0.0)
        boxes_html.append(_bento_box_html(label="Backfillable", value=f"{backfillable_pct:.1f}%", subtitle=f"{backfillable_count:,} incidents"))

    # Unresolved / Cancelled (conditional)
    if show_unresolved_bento:
        unresolved_pct = kpis.get("unresolved_pct", 0.0)
        unresolved_count = kpis.get("unresolved_count", 0)
        boxes_html.append(_bento_box_html(label="Unresolved / Cancelled", value=f"{unresolved_count:,}", subtitle=f"({unresolved_pct:.1f}% of selection)"))

    # Answerable breakdown (conditional)
    if show_answerable_breakdown:
        for value, pct in sorted(breakdown.items()):
            label = value.capitalize() if value else "Unknown"
            boxes_html.append(_bento_box_html(label=f"Self Serve: {label}", value=f"{pct:.1f}%", small_value=True))

    # Avg Cosine Similarity
    cosine_sim = kpis.get("avg_cosine_similarity")
    cosine_display = f"{cosine_sim:.3f}" if cosine_sim is not None and not pd.isna(cosine_sim) else "N/A"
    boxes_html.append(_bento_box_html(label="Avg Cosine Similarity", value=cosine_display))

    # Avg Text Match
    text_match = kpis.get("avg_text_match")
    text_match_display = f"{text_match:.3f}" if text_match is not None and not pd.isna(text_match) else "N/A"
    boxes_html.append(_bento_box_html(label="Avg Text Match", value=text_match_display))

    # Render all boxes in a single HTML flexbox container
    st.markdown(f'<div class="bento-container">{"".join(boxes_html)}</div>', unsafe_allow_html=True)


def render_kb_leaderboard(leaderboard_df: pd.DataFrame) -> None:
    """
    Render the KB Article Leaderboard showing retrieval frequency and average scores.

    Displays articles ranked by how often they were retrieved in searches,
    along with their average performance metrics.
    """
    st.subheader("KB Article Leaderboard")
    st.caption("Articles ranked by retrieval frequency with average performance scores")

    if leaderboard_df.empty:
        st.info("No KB article data available for the current selection.")
        return

    # Prepare display dataframe with formatted columns
    display_df = leaderboard_df.copy()

    # Rename columns for display
    display_df = display_df.rename(
        columns={
            "KB_NUMBER": "KB Article",
            "FREQUENCY": "Times Retrieved",
            "AVG_COSINE_SIMILARITY": "Avg Cosine",
            "AVG_RERANKER_SCORE": "Avg Reranker",
            "AVG_TEXT_MATCH": "Avg Text Match",
            "AVG_CONTEXT_RELEVANCE": "Avg Context Rel.",
        }
    )

    # Format numeric columns
    numeric_cols = ["Avg Cosine", "Avg Reranker", "Avg Text Match", "Avg Context Rel."]
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=min(400, 35 * (len(display_df) + 1)),
    )


def render_data_table(df: pd.DataFrame) -> None:
    """Render the filtered data table with row selection for detail inspection."""

    if df.empty:
        st.info("No data matches the current filters.")
        return

    # Select columns to display in main table
    display_cols = [
        "L1_TAG",
        "L2_TAG",
        "L3_TAG",
        "L4_TAG",
        "query",
        "answerable_with_kb",
        "CONTEXT_RELEVANCE_SCORE",
        "estimated_complexity",
        "SOURCE_TABLE",
    ]

    # Rename columns for display
    column_rename_map = {
        "query": "Service Ticket",
        "answerable_with_kb": "Self Serve Candidate",
        "CONTEXT_RELEVANCE_SCORE": "Context Relevance",
        "estimated_complexity": "Complexity",
        "SOURCE_TABLE": "Source Type",
    }

    # Only include columns that exist
    available_cols = [c for c in display_cols if c in df.columns]

    st.subheader(f"Service Tickets ({len(df):,} records)")
    st.caption("Click a row to inspect details below")

    # Create display dataframe with renamed columns
    display_df = df[available_cols].copy()
    display_df = display_df.rename(columns={k: v for k, v in column_rename_map.items() if k in available_cols})

    # Dataframe with row selection enabled
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=350,
        on_select="rerun",
        selection_mode="single-row",
        key="data_table_selection",
    )

    # Show detail panel if a row is selected
    selected_rows = event.selection.rows

    if selected_rows:
        row_idx = selected_rows[0]
        row = df.iloc[row_idx]

        st.divider()
        render_detail_panel(row)


@st.fragment
def render_detail_panel(row: pd.Series) -> None:
    """
    Render the selected record details panel as a fragment.
    """
    st.subheader("🔍 Selected Record Details")

    query_preview = str(row.get("query", ""))[:80] + "..." if len(str(row.get("query", ""))) > 80 else row.get("query", "")
    score = row.get("CONTEXT_RELEVANCE_SCORE", "N/A")
    score_display = f"{score:.2f}" if pd.notna(score) and score != "N/A" else "N/A"
    st.markdown(f"**Query:** {query_preview}  •  **Score:** {score_display}  •  **Self Serve:** {row.get('answerable_with_kb', 'N/A')}")

    tab_eval, tab_articles, tab_generated, tab_attrs = st.tabs(["📊 Evaluation", "📚 Retrieved Articles", "🤖 Generated", "📋 Ticket Metadata"])

    with tab_eval:
        st.markdown("**Context Relevance Evaluation**")
        st.markdown(f"**Score:** {score_display}")

        reason = row.get("CONTEXT_RELEVANCE_REASON", "")
        if pd.notna(reason) and reason:
            st.markdown("**Chain of Thought Reasoning:**")
            st.markdown(f'<div class="theme-box">{str(reason)}</div>', unsafe_allow_html=True)
        else:
            st.caption("No evaluation reasoning available")

    with tab_articles:
        st.markdown("**Knowledge Articles Retrieved for this Query**")
        st.caption("These are the articles the search system found. If relevant articles exist but aren't shown here, it's a retrieval issue. If no relevant articles exist, it's a knowledge gap.")

        articles = row.get("PARSED_ARTICLES", [])

        if articles and len(articles) > 0:
            # Get raw chunk count for display
            response_raw = row.get("RESPONSE", None)
            chunk_count = 0
            if pd.notna(response_raw) and response_raw:
                if isinstance(response_raw, str):
                    try:
                        chunk_count = len(json.loads(response_raw))
                    except (json.JSONDecodeError, TypeError):
                        chunk_count = len(articles)
                elif isinstance(response_raw, list):
                    chunk_count = len(response_raw)
            else:
                chunk_count = len(articles)

            st.markdown(f"**{len(articles)} unique article(s) retrieved** (from {chunk_count} chunks):")

            for i, article in enumerate(articles):
                summary = article.get("summary", "")
                content = article.get("content", "")
                title = article.get("title") or f"Article {i + 1}"

                # Build score display
                score_parts = []
                if article.get("cosine_similarity") is not None:
                    score_parts.append(f"Cosine: {article['cosine_similarity']:.3f}")
                if article.get("text_match") is not None:
                    score_parts.append(f"Text: {article['text_match']:.3f}")
                if article.get("reranker_score") is not None:
                    score_parts.append(f"Rerank: {article['reranker_score']:.3f}")
                score_str = f" ({' • '.join(score_parts)})" if score_parts else ""

                with st.expander(f"📄 {title}{score_str}", expanded=(i == 0)):
                    # Show summary
                    if summary:
                        st.markdown("**Summary:**")
                        st.markdown(summary)

                    # Show content in scrollable container
                    if content:
                        st.markdown("**Article Content:**")
                        st.markdown(f'<div class="scrollable-content">{content}</div>', unsafe_allow_html=True)
        else:
            st.warning("No articles were retrieved for this query. This indicates a potential knowledge gap or retrieval issue.")

    with tab_generated:
        st.markdown("**Synthetic Pair Generation Output**")
        generated_json = row.get("GENERATED_JSON", {})
        if generated_json and isinstance(generated_json, dict):
            st.json(generated_json)
        else:
            st.caption("No generated data available")

    with tab_attrs:
        st.markdown("**ServiceNow Ticket Metadata**")
        attrs_json = row.get("ATTRS_JSON", {})
        if attrs_json and isinstance(attrs_json, dict):
            st.json(attrs_json)
        else:
            st.caption("No ticket metadata available")

        # Taxonomy path
        taxonomy = f"{row.get('L1_TAG', '')} > {row.get('L2_TAG', '')} > {row.get('L3_TAG', '')} > {row.get('L4_TAG', '')}"
        st.markdown(f"**Taxonomy:** {taxonomy}")


def render_knowledge_gap_panel(session, filtered_df: pd.DataFrame, kpis: dict) -> None:
    """
    Render the AI-generated knowledge gap summary as a bento box.
    Empty state shows a generate button; filled state shows the AI summary.
    Uses AI_AGG to analyze context relevance chain-of-thought evaluations on-demand.
    """
    from data import generate_knowledge_gap_summary
    from store import SetAISummaryAction

    store = get_store()
    avg_score = kpis.get("avg_context_relevance", 0) or 0

    # If loading, trigger the actual generation (after showing loading UI)
    if store.ai_summary_loading:
        # Show loading state
        st.markdown(
            """
        <div class="kg-panel kg-panel-loading">
            <div class="kg-title">
                🤖 Knowledge Gap Analysis
            </div>
            <div style="font-size: 24px; margin: 20px 0;">⏳</div>
            <div class="kg-subtitle">
                Analyzing evaluations with AI_AGG...
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Run the generation
        try:
            summary = generate_knowledge_gap_summary(session, filtered_df)
            dispatch(SetAISummaryAction(loading=False, summary=summary))
        except Exception as e:
            dispatch(SetAISummaryAction(loading=False, summary=f"Error: {str(e)}"))
        st.rerun()
        return

    if store.ai_summary:
        # Filled state: Show the AI summary
        st.markdown(
            f"""
        <div class="kg-panel">
            <div class="kg-header">
                <div class="kg-title">
                    🤖 Knowledge Gap Analysis
                </div>
                <div class="kg-meta">
                    {len(filtered_df):,} tickets • Avg Score: {avg_score:.2f}
                </div>
            </div>
            <div class="kg-content">
                {store.ai_summary}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Buttons directly below with minimal spacing
        col1, col2, col3 = st.columns([1, 1, 6])
        with col1:
            if st.button("🔄 Regenerate", key="btn_regenerate_summary"):
                dispatch(SetAISummaryAction(loading=True, summary=None))
                st.rerun()
        with col2:
            if st.button("Clear", key="btn_clear_summary"):
                dispatch(SetAISummaryAction(loading=False, summary=None))
                st.rerun()

    else:
        # Empty state with centered button
        st.markdown(
            f"""
        <div class="kg-panel kg-panel-empty">
            <div class="kg-title" style="margin-bottom: 8px;">
                🤖 Knowledge Gap Analysis
            </div>
            <div class="kg-subtitle">
                Analyze {len(filtered_df):,} service tickets
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Centered button directly below
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button(
                "🔍 Analyze",
                key="btn_generate_summary",
                disabled=filtered_df.empty,
                type="primary",
                use_container_width=True,
            ):
                dispatch(SetAISummaryAction(loading=True, summary=None))
                st.rerun()


def render_debug_panel(
    merged_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    grouped_df: pd.DataFrame,
) -> None:
    """Debug panel showing intermediate data states."""

    with st.expander("Debug: Data State"):
        st.write("**Store State:**")
        st.json(get_store().model_dump())

        st.write(f"**Merged Data Shape:** {merged_df.shape}")
        st.write(f"**Filtered Data Shape:** {filtered_df.shape}")
        st.write(f"**Grouped Data Shape:** {grouped_df.shape}")

        st.write("**Merged Data Sample (5 rows):**")
        st.dataframe(merged_df.head(5))

        st.write("**Grouped Data:**")
        st.dataframe(grouped_df)
