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
    get_merged_data,
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

    # Header
    st.title("Knowledge Base Gap Analysis")
    st.markdown(
        "Identify gaps in the knowledge base by analyzing synthetic ticket queries, "
        "context relevance scores, and deflection potential."
    )

    # Load data
    try:
        session = get_session()
        merged_df = get_merged_data(session)
        source_types = get_source_types(session)
        answerable_options = get_answerable_options(session)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    if merged_df.empty:
        st.warning("No data available. Please check the data pipeline.")
        st.stop()

    # Initialize store filters from actual data (only on first load when empty)
    dispatch(InitializeFiltersAction(
        source_types=source_types,
        answerable_options=answerable_options
    ))

    # Re-fetch store after potential initialization
    store = get_store()

    # Refresh button
    col_refresh, col_spacer = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # Apply filters to get filtered dataset
    filtered_df = filter_data(
        df=merged_df,
        source_types=store.source_types,
        answerable_filter=store.answerable_filter,
        selected_l1=store.selected_l1,
        selected_l2=store.selected_l2,
        selected_l3=store.selected_l3,
        selected_l4=store.selected_l4,
    )

    # Prepare sunburst data - filtered by taxonomy selection to "zoom in"
    # Sunburst shows the selected subtree (or all data if nothing selected)
    grouped_df, path_cols = prepare_sunburst_data(
        df=filtered_df,
        show_l1=True,
        show_l2=True,
        show_l3=True,
        show_l4=True,
    )

    # Taxonomy drill-down selector (cascading dropdowns)
    # Uses unfiltered data (by taxonomy) to show all options
    taxonomy_df = filter_data(
        df=merged_df,
        source_types=store.source_types,
        answerable_filter=store.answerable_filter,
    )
    render_taxonomy_selector(taxonomy_df)

    # Sunburst visualization - zooms based on taxonomy selection
    render_sunburst(grouped_df, path_cols)

    # Show selection info
    if any([store.selected_l1, store.selected_l2, store.selected_l3, store.selected_l4]):
        st.info(f"Showing {len(filtered_df):,} records for selected taxonomy path")
    else:
        st.caption(f"Showing all {len(filtered_df):,} records")

    st.divider()

    # Filters above the data table
    render_filters(source_types, answerable_options)

    # Data table
    render_data_table(filtered_df)

    st.divider()

    # Compute KPIs once for reuse
    kpis = compute_kpis(filtered_df)

    # KPI Bento boxes
    st.subheader("Key Metrics")
    render_kpi_bento(kpis)

    st.divider()

    # Knowledge gap analysis bento (on-demand AI_AGG)
    render_knowledge_gap_panel(session, filtered_df, kpis)

    # Debug panel (collapsible)
    render_debug_panel(merged_df, filtered_df, grouped_df)


if __name__ == "__main__":
    main()
