"""
UI components for the Sunburst Push-Down Taxonomy application.
Each component is a pure function that renders UI based on state.
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from store import (
    ClearSelectionAction,
    SetAnswerableFilterAction,
    SetSelectedPathAction,
    SetSourceTypesAction,
    dispatch,
    get_store,
)


def render_sunburst(grouped_df: pd.DataFrame, path_cols: list[str]) -> None:
    """
    Render the interactive sunburst chart (visualization only).
    Selection is handled by separate breadcrumb controls.
    """
    if grouped_df.empty:
        st.warning("No data available for sunburst visualization.")
        return

    # Create sunburst
    fig = px.sunburst(
        grouped_df,
        path=path_cols,
        values="QUERY_COUNT",
        color="CONTEXT_RELEVANCE_SCORE",
        color_continuous_scale="Blues",
        title="Taxonomy Distribution by Query Count",
    )

    fig.update_layout(
        height=600,
        margin={"t": 50, "l": 0, "r": 0, "b": 0},
    )

    # Render chart (visualization only, no click handling)
    st.plotly_chart(fig, use_container_width=True, key="sunburst_chart")


def render_taxonomy_selector(df: pd.DataFrame) -> None:
    """
    Render cascading dropdowns for taxonomy level selection.
    Each level filters the options available in the next level.
    """
    store = get_store()

    st.markdown("**Filter by Taxonomy:**")

    col1, col2, col3, col4, col_clear = st.columns([2, 2, 2, 2, 1])

    # L1 selector
    with col1:
        l1_options = ["All"] + sorted(df["L1_TAG"].dropna().unique().tolist())
        l1_default = store.selected_l1 if store.selected_l1 in l1_options else "All"
        l1_index = l1_options.index(l1_default) if l1_default in l1_options else 0

        st.selectbox(
            "L1",
            options=l1_options,
            index=l1_index,
            key="sel_l1",
            on_change=lambda: dispatch(
                SetSelectedPathAction(
                    l1=st.session_state.sel_l1 if st.session_state.sel_l1 != "All" else None,
                    l2=None, l3=None, l4=None  # Reset children on parent change
                )
            )
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
            "L2",
            options=l2_options,
            index=l2_index,
            key="sel_l2",
            disabled=not store.selected_l1,
            on_change=lambda: dispatch(
                SetSelectedPathAction(
                    l1=store.selected_l1,
                    l2=st.session_state.sel_l2 if st.session_state.sel_l2 != "All" else None,
                    l3=None, l4=None  # Reset children
                )
            )
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
            "L3",
            options=l3_options,
            index=l3_index,
            key="sel_l3",
            disabled=not store.selected_l2,
            on_change=lambda: dispatch(
                SetSelectedPathAction(
                    l1=store.selected_l1,
                    l2=store.selected_l2,
                    l3=st.session_state.sel_l3 if st.session_state.sel_l3 != "All" else None,
                    l4=None  # Reset child
                )
            )
        )

    # L4 selector - filtered by L1 + L2 + L3
    with col4:
        if store.selected_l1 and store.selected_l2 and store.selected_l3:
            l4_df = df[
                (df["L1_TAG"] == store.selected_l1) &
                (df["L2_TAG"] == store.selected_l2) &
                (df["L3_TAG"] == store.selected_l3)
            ]
        else:
            l4_df = pd.DataFrame()
        l4_options = ["All"] + sorted(l4_df["L4_TAG"].dropna().unique().tolist()) if not l4_df.empty else ["All"]
        l4_default = store.selected_l4 if store.selected_l4 in l4_options else "All"
        l4_index = l4_options.index(l4_default) if l4_default in l4_options else 0

        st.selectbox(
            "L4",
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
            )
        )

    # Clear button
    with col_clear:
        st.markdown("<br>", unsafe_allow_html=True)  # Align with dropdowns
        if st.button("Clear", key="btn_clear_taxonomy"):
            dispatch(ClearSelectionAction())
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


def render_filters(source_types: list[str], answerable_options: list[str]) -> None:
    """Render filter controls for source type and answerable_with_kb."""
    store = get_store()

    # Give filters more breathing room with 3 columns (2 for filters, 1 spacer)
    col1, col2, col_spacer = st.columns([2, 2, 3])

    with col1:
        # Use store values only if they're valid options, otherwise use all options
        source_default = [s for s in store.source_types if s in source_types]
        if not source_default:
            source_default = source_types

        st.multiselect(
            "Source Type",
            options=source_types,
            default=source_default,
            key="ms_source_types",
            on_change=lambda: dispatch(
                SetSourceTypesAction(source_types=st.session_state.ms_source_types)
            )
        )

    with col2:
        # Use store values only if they're valid options, otherwise use all options
        answerable_default = [a for a in store.answerable_filter if a in answerable_options]
        if not answerable_default:
            answerable_default = answerable_options

        st.multiselect(
            "Answerable by KB",
            options=answerable_options,
            default=answerable_default,
            key="ms_answerable",
            on_change=lambda: dispatch(
                SetAnswerableFilterAction(values=st.session_state.ms_answerable)
            )
        )


def render_kpi_bento(kpis: dict) -> None:
    """Render KPI metrics as bento box cards with visual styling."""

    # CSS for bento box styling
    st.markdown("""
    <style>
    .bento-box {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .bento-label {
        font-size: 14px;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 8px;
    }
    .bento-value {
        font-size: 32px;
        font-weight: bold;
        color: white;
    }
    .bento-value-small {
        font-size: 24px;
        font-weight: bold;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    # First row: Query Count and Context Relevance
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="bento-box">
            <div class="bento-label">Query Count</div>
            <div class="bento-value">{kpis['query_count']:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        relevance = kpis['avg_context_relevance']
        relevance_display = f"{relevance:.2f}" if relevance is not None and not pd.isna(relevance) else "N/A"
        st.markdown(f"""
        <div class="bento-box">
            <div class="bento-label">Avg Context Relevance</div>
            <div class="bento-value">{relevance_display}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Second row: Answerable by KB breakdown
    breakdown = kpis.get('answerable_breakdown', {})

    if breakdown:
        cols = st.columns(len(breakdown))
        for i, (value, pct) in enumerate(sorted(breakdown.items())):
            with cols[i]:
                label = value.capitalize() if value else "Unknown"
                st.markdown(f"""
                <div class="bento-box">
                    <div class="bento-label">Answerable: {label}</div>
                    <div class="bento-value-small">{pct:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)


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

    # Only include columns that exist
    available_cols = [c for c in display_cols if c in df.columns]

    st.subheader(f"Synthetic Pairs ({len(df):,} records)")
    st.caption("Click a row to inspect details below")

    # Dataframe with row selection enabled
    event = st.dataframe(
        df[available_cols],
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
        st.subheader("🔍 Selected Record Details")

        # Summary line
        query_preview = str(row.get('query', ''))[:80] + "..." if len(str(row.get('query', ''))) > 80 else row.get('query', '')
        score = row.get('CONTEXT_RELEVANCE_SCORE', 'N/A')
        score_display = f"{score:.2f}" if pd.notna(score) and score != 'N/A' else 'N/A'
        st.markdown(f"**Query:** {query_preview}  •  **Score:** {score_display}  •  **Answerable:** {row.get('answerable_with_kb', 'N/A')}")

        # Tabs for different data sources
        tab_eval, tab_generated, tab_attrs = st.tabs(["📊 Evaluation", "🤖 Generated", "📋 Ticket Metadata"])

        with tab_eval:
            st.markdown("**Context Relevance Evaluation**")
            st.markdown(f"**Score:** {score_display}")

            reason = row.get('CONTEXT_RELEVANCE_REASON', '')
            if pd.notna(reason) and reason:
                st.markdown("**Chain of Thought Reasoning:**")
                st.code(str(reason), language=None)
            else:
                st.caption("No evaluation reasoning available")

        with tab_generated:
            st.markdown("**Synthetic Pair Generation Output**")

            generated_data = {
                "query": row.get('query', ''),
                "answerable_with_kb": row.get('answerable_with_kb', ''),
                "rationale": row.get('rationale', ''),
                "expected_response": row.get('expected_response', ''),
                "estimated_complexity": row.get('estimated_complexity', ''),
                "recommendation": row.get('recommendation', ''),
            }
            # Filter out empty values
            generated_data = {k: v for k, v in generated_data.items() if pd.notna(v) and v != ''}
            st.json(generated_data)

        with tab_attrs:
            st.markdown("**ServiceNow Ticket Metadata**")

            attrs_data = {
                "SHORT_DESCRIPTION": row.get('SHORT_DESCRIPTION', ''),
                "CATEGORY": row.get('CATEGORY', ''),
                "U_ITS_SYMPTOM_BTS": row.get('U_ITS_SYMPTOM_BTS', ''),
                "U_RESOLUTION_CODE_BTS": row.get('U_RESOLUTION_CODE_BTS', ''),
                "U_RESOLUTION_BTS": row.get('U_RESOLUTION_BTS', ''),
                "U_RESOLUTION_NOTES_BTS": row.get('U_RESOLUTION_NOTES_BTS', ''),
            }
            # Filter out empty values
            attrs_data = {k: v for k, v in attrs_data.items() if pd.notna(v) and v != ''}
            st.json(attrs_data)

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
        st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 40px;
            text-align: center;
        ">
            <div style="font-size: 14px; color: rgba(255, 255, 255, 0.7);">
                🤖 Knowledge Gap Analysis
            </div>
            <div style="font-size: 24px; margin: 20px 0;">⏳</div>
            <div style="color: rgba(255, 255, 255, 0.6); font-size: 14px;">
                Analyzing evaluations with AI_AGG...
            </div>
        </div>
        """, unsafe_allow_html=True)

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
        st.markdown(f"""
        <div style="
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 8px;
        ">
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
            ">
                <div style="font-size: 14px; color: rgba(255, 255, 255, 0.7);">
                    🤖 Knowledge Gap Analysis
                </div>
                <div style="font-size: 12px; color: rgba(255, 255, 255, 0.5);">
                    {len(filtered_df):,} evaluations • Avg Score: {avg_score:.2f}
                </div>
            </div>
            <div style="color: white; font-size: 15px; line-height: 1.8;">
                {store.ai_summary}
            </div>
        </div>
        """, unsafe_allow_html=True)

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
        st.markdown(f"""
        <div style="
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 32px;
            text-align: center;
            margin-bottom: 8px;
        ">
            <div style="font-size: 14px; color: rgba(255, 255, 255, 0.7); margin-bottom: 8px;">
                🤖 Knowledge Gap Analysis
            </div>
            <div style="font-size: 13px; color: rgba(255, 255, 255, 0.5);">
                Analyze {len(filtered_df):,} context relevance evaluations
            </div>
        </div>
        """, unsafe_allow_html=True)

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
