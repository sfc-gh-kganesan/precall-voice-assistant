import altair as alt
import pandas as pd
import streamlit as st
from data_operations import SnowflakeDataOperations


def render_taxonomy_tab(data_ops: SnowflakeDataOperations) -> None:
    st.header("Taxonomy Analysis")
    st.caption("Analyze evaluation metrics by taxonomy levels from synthetic queries.")

    # Level selection as multiselect for hierarchical grouping
    all_levels = ["L1_TAG", "L2_TAG", "L3_TAG", "L4_TAG"]

    selected_levels = st.multiselect(
        "Group by Taxonomy Levels",
        options=all_levels,
        default=["L1_TAG"],
        format_func=lambda x: x.replace("_TAG", "").replace("L", "Level "),
        key="taxonomy_levels",
        help="Select multiple levels to see hierarchical breakdown",
    )

    if not selected_levels:
        st.info("Select at least one taxonomy level to view the analysis.")
        return

    # Sort levels to maintain hierarchy order
    selected_levels = sorted(selected_levels, key=lambda x: all_levels.index(x))

    # Get data grouped by selected levels
    summary_df = data_ops.get_taxonomy_summary_by_levels(selected_levels)

    if summary_df.empty:
        st.warning("No taxonomy data available. Run evaluations on synthetic queries first.")
        return

    # Summary metrics
    total_queries = summary_df["QUERY_COUNT"].sum()
    total_evaluated = summary_df["EVALUATED_COUNT"].sum()
    eval_coverage = (total_evaluated / total_queries * 100) if total_queries > 0 else 0

    # Calculate overall average context relevance
    avg_context_relevance = None
    if "AVG_CONTEXT_RELEVANCE" in summary_df.columns:
        # Weighted average by query count
        valid_rows = summary_df[summary_df["AVG_CONTEXT_RELEVANCE"].notna()]
        if not valid_rows.empty:
            weighted_sum = (valid_rows["AVG_CONTEXT_RELEVANCE"] * valid_rows["EVALUATED_COUNT"]).sum()
            total_weight = valid_rows["EVALUATED_COUNT"].sum()
            if total_weight > 0:
                avg_context_relevance = weighted_sum / total_weight

    # Display metrics
    if avg_context_relevance is not None:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Queries", int(total_queries))
        m2.metric("Evaluated", int(total_evaluated))
        m3.metric("Coverage", f"{eval_coverage:.0f}%")
        m4.metric("Avg Context Relevance", f"{avg_context_relevance:.3f}")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Queries", int(total_queries))
        m2.metric("Evaluated", int(total_evaluated))
        m3.metric("Coverage", f"{eval_coverage:.0f}%")

    st.divider()

    # Build display dataframe with hierarchy
    display_df = summary_df.copy()

    # Rename level columns for display
    level_renames = {level: level.replace("_TAG", "") for level in selected_levels}
    display_df = display_df.rename(columns=level_renames)
    display_level_cols = [level.replace("_TAG", "") for level in selected_levels]

    # Check if we have evaluation data
    has_evaluations = summary_df["EVALUATED_COUNT"].sum() > 0

    if not has_evaluations:
        st.info("No evaluations found for synthetic queries. Run evaluations from the Evaluation tab first.")
        st.subheader("Taxonomy Distribution")
        st.dataframe(
            display_df[display_level_cols + ["QUERY_COUNT"]].rename(columns={"QUERY_COUNT": "Queries"}),
            use_container_width=True,
            hide_index=True,
        )
        return

    # === Context Relevance Chart ===
    st.subheader("Context Relevance by Taxonomy")

    if "AVG_CONTEXT_RELEVANCE" in summary_df.columns and summary_df["AVG_CONTEXT_RELEVANCE"].notna().any():
        # Create a combined label for the x-axis when multiple levels selected
        chart_df = summary_df.copy()

        if len(selected_levels) == 1:
            chart_df["LABEL"] = chart_df[selected_levels[0]].fillna("(empty)")
        else:
            # Combine levels into a hierarchical label
            chart_df["LABEL"] = chart_df[selected_levels].fillna("").apply(
                lambda row: " > ".join([str(v) for v in row if v]), axis=1
            )

        chart_df = chart_df[chart_df["AVG_CONTEXT_RELEVANCE"].notna()]

        if not chart_df.empty:
            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X("LABEL:N", title="Taxonomy", sort="-y"),
                    y=alt.Y("AVG_CONTEXT_RELEVANCE:Q", title="Avg Context Relevance", scale=alt.Scale(domain=[0, 1])),
                    color=alt.Color(
                        "AVG_CONTEXT_RELEVANCE:Q",
                        scale=alt.Scale(scheme="redyellowgreen"),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("LABEL:N", title="Taxonomy"),
                        alt.Tooltip("AVG_CONTEXT_RELEVANCE:Q", title="Avg Context Relevance", format=".3f"),
                        alt.Tooltip("QUERY_COUNT:Q", title="Total Queries"),
                        alt.Tooltip("EVALUATED_COUNT:Q", title="Evaluated"),
                    ],
                )
                .properties(height=400)
            )

            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No context relevance data available yet.")
    else:
        st.info("No context relevance data available. Run evaluations with 'Context Relevance' metric.")

    st.divider()

    # === Detailed Breakdown Table ===
    st.subheader("Detailed Breakdown")

    # Format the display dataframe
    table_df = display_df.copy()

    # Select and rename columns
    base_cols = display_level_cols + ["QUERY_COUNT", "EVALUATED_COUNT"]
    metric_cols = []

    col_renames = {
        "QUERY_COUNT": "Queries",
        "EVALUATED_COUNT": "Evaluated",
    }

    if "AVG_CONTEXT_RELEVANCE" in table_df.columns:
        metric_cols.append("AVG_CONTEXT_RELEVANCE")
        col_renames["AVG_CONTEXT_RELEVANCE"] = "Avg Context Relevance"

    if "AVG_ANSWER_RELEVANCE" in table_df.columns:
        metric_cols.append("AVG_ANSWER_RELEVANCE")
        col_renames["AVG_ANSWER_RELEVANCE"] = "Avg Answer Relevance"

    if "AVG_COMPREHENSIVENESS" in table_df.columns:
        metric_cols.append("AVG_COMPREHENSIVENESS")
        col_renames["AVG_COMPREHENSIVENESS"] = "Avg Comprehensiveness"

    if "AVG_HARMFULNESS" in table_df.columns:
        metric_cols.append("AVG_HARMFULNESS")
        col_renames["AVG_HARMFULNESS"] = "Avg Harmfulness"

    table_df = table_df[base_cols + metric_cols].rename(columns=col_renames)

    # Format metric columns
    for col in ["Avg Context Relevance", "Avg Answer Relevance", "Avg Comprehensiveness", "Avg Harmfulness"]:
        if col in table_df.columns:
            table_df[col] = table_df[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "-")

    st.dataframe(table_df, use_container_width=True, hide_index=True)

    # === Expandable full rollup ===
    with st.expander("Full Taxonomy Rollup (All Levels)"):
        full_df = data_ops.get_taxonomy_evaluation_rollup()
        if not full_df.empty:
            # Format the full rollup
            for col in ["AVG_ANSWER_RELEVANCE", "AVG_CONTEXT_RELEVANCE", "AVG_COMPREHENSIVENESS", "AVG_HARMFULNESS"]:
                if col in full_df.columns:
                    full_df[col] = full_df[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "-")
            st.dataframe(full_df, use_container_width=True, hide_index=True)
        else:
            st.info("No data available.")
