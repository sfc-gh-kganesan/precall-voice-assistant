"""
Sunburst Push-Down Taxonomy Application

Interactive Streamlit application for exploring synthetic pair evaluation data
with hierarchical taxonomy drill-down capabilities.

Database: emea_elementum_ace_dev
Schema: sf_fde
"""

import streamlit as st

# Configure page
st.set_page_config(
    page_title="KB Gap Analysis",
    page_icon="🔍",
    layout="wide",
)

# Import modules after st.set_page_config
from components import (
    inject_app_styles,
    render_data_table,
    render_debug_panel,
    render_filters,
    render_knowledge_gap_panel,
    render_kpi_bento,
    render_sunburst,
    render_taxonomy_selector,
)
from data import (
    compute_kpis,
    filter_data,
    get_answerable_options,
    get_backfillable_options,
    get_merged_data,
    get_resolution_options,
    get_session,
    get_source_types,
    prepare_sunburst_data,
)
from store import InitializeFiltersAction, dispatch, get_store, init_store


def main():
    """Main application entry point."""

    # Initialize state
    init_store()
    store = get_store()

    # Inject CSS styles (once, before any UI)
    inject_app_styles()

    # Header
    st.title("Knowledge Base Gap Analysis")
    st.markdown("Identify gaps in the knowledge base by analyzing synthetic ticket queries, context relevance scores, and deflection potential.")

    # Load data
    try:
        session = get_session()
        merged_df = get_merged_data(session)
        source_types = get_source_types(session)
        answerable_options = get_answerable_options(session)
        resolution_options = get_resolution_options()
        backfillable_options = get_backfillable_options()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    if merged_df.empty:
        st.warning("No data available. Please check the data pipeline.")
        st.stop()

    # Initialize store filters from actual data (only on first load when empty)
    dispatch(InitializeFiltersAction(source_types=source_types, answerable_options=answerable_options, resolution_options=resolution_options, backfillable_options=backfillable_options))

    # Re-fetch store after potential initialization
    store = get_store()

    # Refresh button
    col_refresh, col_spacer = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # Filters at the top
    render_filters(source_types, answerable_options, resolution_options, backfillable_options)

    # Apply dropdown filters once (shared by taxonomy selector and main data)
    base_filtered_df = filter_data(
        df=merged_df,
        source_types=store.source_types,
        answerable_filter=store.answerable_filter,
        resolution_filter=store.resolution_filter,
        backfillable_filter=store.backfillable_filter,
        all_source_types=source_types,
        all_answerable_options=answerable_options,
    )

    # Apply taxonomy selection on top for main data
    filtered_df = base_filtered_df
    if store.selected_l1:
        filtered_df = filtered_df[filtered_df["L1_TAG"] == store.selected_l1]
    if store.selected_l2:
        filtered_df = filtered_df[filtered_df["L2_TAG"] == store.selected_l2]
    if store.selected_l3:
        filtered_df = filtered_df[filtered_df["L3_TAG"] == store.selected_l3]
    if store.selected_l4:
        filtered_df = filtered_df[filtered_df["L4_TAG"] == store.selected_l4]

    # Prepare sunburst data - filtered by taxonomy selection to "zoom in"
    grouped_df, path_cols = prepare_sunburst_data(
        df=filtered_df,
        show_l1=True,
        show_l2=True,
        show_l3=True,
        show_l4=True,
    )

    with st.expander("📖 Glossary", expanded=False):
        st.markdown(
            "- **Level (L1-L4)**: Bottom-up ontology for a ticket, from broad category (L1) to specific issue type (L4).\n"
            "- **Self Serve Candidate**: Whether this ticket type *could potentially* be resolved "
            "via self-service (knowledge base, chatbot, FAQ). Values: `full` (fully self-serve), "
            "`partial` (needs some human help), `no` (requires human intervention). "
            "This is about the *nature* of the issue, not whether KB articles currently exist.\n"
            "- **Backfillable**: Incidents with non-trivial resolution notes that could be used to create or improve KB articles. "
            "These notes document how issues were resolved and can serve as source material for knowledge. "
            "(Applies to incidents only; service requests don't have resolution notes.)\n"
            "- **Coverage**: Percentage of tickets where retrieval found relevant knowledge (context relevance ≥ 0.8).\n"
            "- **Context Relevance**: How relevant the retrieved knowledge articles are to the query (0-1 scale).\n"
            "- **Unresolved / Cancelled**: Tickets closed without resolution (aged out, duplicates, or user-cancelled)."
        )

    # Taxonomy selector uses base_filtered_df (without taxonomy filter) to show all options
    render_taxonomy_selector(base_filtered_df)

    st.divider()

    # Sunburst visualization - zooms based on taxonomy selection
    render_sunburst(grouped_df, path_cols)

    # Show selection info
    if any([store.selected_l1, store.selected_l2, store.selected_l3, store.selected_l4]):
        st.info(f"Showing {len(filtered_df):,} tickets for selected taxonomy path")
    else:
        st.caption(f"Showing all {len(filtered_df):,} tickets")

    # Data table
    render_data_table(filtered_df)

    st.divider()

    # Compute KPIs once for reuse (pass total population for percentage calculation)
    kpis = compute_kpis(filtered_df, total_population=len(merged_df))

    # KPI Bento boxes
    st.subheader("Key Metrics")
    render_kpi_bento(kpis, resolution_filter=store.resolution_filter, backfillable_filter=store.backfillable_filter)

    st.divider()

    # Knowledge gap analysis bento (on-demand AI_AGG)
    render_knowledge_gap_panel(session, filtered_df, kpis)

    # Debug panel (collapsible)
    render_debug_panel(merged_df, filtered_df, grouped_df)


if __name__ == "__main__":
    main()
