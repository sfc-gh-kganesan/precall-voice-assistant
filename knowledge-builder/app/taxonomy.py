import pandas as pd
import plotly.express as px
import streamlit as st
from snowflake.snowpark import Session


def get_hierarchy_level(row: pd.Series) -> str:
    """Determine the hierarchy level of a rollup row."""
    if pd.isna(row["L1_TAG"]):
        return "Grand Total"
    elif pd.isna(row["L2_TAG"]):
        return "L1 Total"
    elif pd.isna(row["L3_TAG"]):
        return "L2 Total"
    elif pd.isna(row["L4_TAG"]):
        return "L3 Total"
    else:
        return "Detail"


def create_hierarchy_label(row: pd.Series) -> str:
    """Create a display label for the hierarchy."""
    if pd.isna(row["L1_TAG"]):
        return "All Categories"
    elif pd.isna(row["L2_TAG"]):
        return row["L1_TAG"]
    elif pd.isna(row["L3_TAG"]):
        return f"{row['L1_TAG']} > {row['L2_TAG']}"
    elif pd.isna(row["L4_TAG"]):
        return f"{row['L1_TAG']} > {row['L2_TAG']} > {row['L3_TAG']}"
    else:
        return f"{row['L1_TAG']} > {row['L2_TAG']} > {row['L3_TAG']} > {row['L4_TAG']}"


def load_taxonomy_data(session: Session) -> pd.DataFrame:
    """Load taxonomy rollup data from Snowflake."""
    query = """
    WITH EVALS AS (
        SELECT ER.SEARCH_ID,
               ER.INPUT_QUERY,
               ER.CHUNKS,
               ER.EVALUATION_MODEL,
               E.VALUE['relevance']['score']::INT AS RELEVANCE_SCORE,
               E.VALUE['relevance']['reasons']['reason']::VARCHAR AS RELEVANCE_REASON,
               E.VALUE['context_relevance']['reasons']['reason']::VARCHAR AS CONTEXT_RELEVANCE_REASON,
               E.VALUE['context_relevance']['score']::VARCHAR AS CONTEXT_RELEVANCE_SCORE
        FROM EVALUATION_RESULTS AS ER,
        LATERAL FLATTEN ("EVALUATION") AS E
        QUALIFY ROW_NUMBER() OVER (PARTITION BY ER.SEARCH_ID ORDER BY NULL) = 1
    ),
    TAXONOMIES AS (
        SELECT GENERATED['query']::VARCHAR AS INPUT_QUERY,
               L1_RAW,
               L1_TAG,
               L2_RAW,
               L2_TAG,
               L3_RAW,
               L3_TAG,
               L4_RAW,
               L4_TAG,
               RELEVANCE_SCORE,
               RELEVANCE_REASON,
               CONTEXT_RELEVANCE_SCORE,
               CONTEXT_RELEVANCE_REASON
        FROM SYNTHETIC_PAIRS AS SP
        INNER JOIN EVALS AS E ON SP.GENERATED['query']::VARCHAR = E.INPUT_QUERY
        QUALIFY ROW_NUMBER() OVER (PARTITION BY INPUT_QUERY ORDER BY NULL) = 1
    ),
    ROLLING AS (
        SELECT
            L1_TAG,
            L2_TAG,
            L3_TAG,
            L4_TAG,
            COUNT(*) AS QUERY_COUNT,
            ROUND(AVG(RELEVANCE_SCORE), 2) AS AVG_RELEVANCE_SCORE,
            ROUND(AVG(CONTEXT_RELEVANCE_SCORE), 2) AS AVG_CONTEXT_RELEVANCE_SCORE
        FROM TAXONOMIES
        GROUP BY ROLLUP(L1_TAG, L2_TAG, L3_TAG, L4_TAG)
        ORDER BY
            L1_TAG NULLS LAST,
            L2_TAG NULLS LAST,
            L3_TAG NULLS LAST,
            L4_TAG NULLS LAST
    )
    SELECT L1_TAG,
           L2_TAG,
           L3_TAG,
           L4_TAG,
           QUERY_COUNT,
           AVG_RELEVANCE_SCORE,
           AVG_CONTEXT_RELEVANCE_SCORE
    FROM ROLLING
    """
    return session.sql(query).to_pandas()


def render_taxonomy_tab(session: Session) -> None:
    st.header("Quality Coverage")
    st.caption("Hierarchical view of query evaluation scores by taxonomy category")

    df = load_taxonomy_data(session)

    if df.empty:
        st.warning("No evaluation data available. Run evaluations on synthetic queries first.")
        return

    df["LEVEL"] = df.apply(get_hierarchy_level, axis=1)
    df["HIERARCHY_LABEL"] = df.apply(create_hierarchy_label, axis=1)

    grand_total = df[df["LEVEL"] == "Grand Total"]
    grand_total_row = grand_total.iloc[0] if len(grand_total) > 0 else None

    st.subheader("Overall Summary")
    col1, col2, col3 = st.columns(3)

    if grand_total_row is not None:
        with col1:
            st.metric("Total Evaluated Queries", int(grand_total_row["QUERY_COUNT"]))
        with col2:
            relevance = grand_total_row["AVG_RELEVANCE_SCORE"]
            st.metric("Avg Relevance Score", f"{relevance:.2f}" if pd.notna(relevance) else "N/A")
        with col3:
            context = grand_total_row["AVG_CONTEXT_RELEVANCE_SCORE"]
            st.metric("Avg Context Relevance", f"{context:.2f}" if pd.notna(context) else "N/A")

    st.divider()

    st.subheader("Explore by Taxonomy Level")

    level_filter = st.selectbox(
        "Select rollup level to view",
        options=["All Levels", "L1 Total", "L2 Total", "L3 Total", "Detail"],
        index=0,
        key="taxonomy_level_filter",
    )

    if level_filter == "All Levels":
        filtered_df = df[df["LEVEL"] != "Grand Total"]
    else:
        filtered_df = df[df["LEVEL"] == level_filter]

    l1_categories = df[df["L1_TAG"].notna()]["L1_TAG"].unique().tolist()
    if l1_categories:
        selected_l1 = st.multiselect(
            "Filter by L1 Category",
            options=l1_categories,
            default=[],
            key="taxonomy_l1_filter",
        )
        if selected_l1:
            filtered_df = filtered_df[filtered_df["L1_TAG"].isin(selected_l1)]

    tab1, tab2, tab3 = st.tabs(["Table View", "Charts", "Sunburst"])

    with tab1:
        st.markdown("**Taxonomy Rollup Data**")

        display_df = filtered_df[["HIERARCHY_LABEL", "LEVEL", "QUERY_COUNT", "AVG_RELEVANCE_SCORE", "AVG_CONTEXT_RELEVANCE_SCORE"]].copy()
        display_df.columns = ["Category Path", "Level", "Query Count", "Avg Relevance", "Avg Context Relevance"]

        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("**Score Distribution by Category**")

        l1_data = df[df["LEVEL"] == "L1 Total"].copy()

        if not l1_data.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Query Count by L1 Category**")
                fig_count = px.bar(
                    l1_data,
                    x="L1_TAG",
                    y="QUERY_COUNT",
                    color="L1_TAG",
                    labels={"L1_TAG": "Category", "QUERY_COUNT": "Query Count"},
                )
                fig_count.update_layout(showlegend=False)
                st.plotly_chart(fig_count, use_container_width=True)

            with col2:
                st.markdown("**Average Scores by L1 Category**")
                score_cols = ["AVG_RELEVANCE_SCORE", "AVG_CONTEXT_RELEVANCE_SCORE"]
                if l1_data[score_cols].notna().any().any():
                    melted = l1_data.melt(
                        id_vars=["L1_TAG"],
                        value_vars=score_cols,
                        var_name="Score Type",
                        value_name="Score",
                    )
                    melted["Score Type"] = melted["Score Type"].map(
                        {
                            "AVG_RELEVANCE_SCORE": "Relevance",
                            "AVG_CONTEXT_RELEVANCE_SCORE": "Context Relevance",
                        }
                    )

                    fig_scores = px.bar(
                        melted,
                        x="L1_TAG",
                        y="Score",
                        color="Score Type",
                        barmode="group",
                        labels={"L1_TAG": "Category", "Score": "Average Score"},
                    )
                    st.plotly_chart(fig_scores, use_container_width=True)
                else:
                    st.info("No score data available for visualization.")
        else:
            st.info("No L1 category data available for charts.")

        detail_data = df[df["LEVEL"] == "Detail"].copy()
        if not detail_data.empty and len(detail_data) > 1:
            st.markdown("**Query Count by Full Taxonomy Path**")
            fig_detail = px.bar(
                detail_data.head(20),
                x="HIERARCHY_LABEL",
                y="QUERY_COUNT",
                color="L1_TAG",
                labels={"HIERARCHY_LABEL": "Taxonomy Path", "QUERY_COUNT": "Query Count"},
            )
            fig_detail.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_detail, use_container_width=True)

    with tab3:
        st.markdown("**Hierarchical Sunburst View**")

        detail_data = df[df["LEVEL"] == "Detail"].copy()

        if not detail_data.empty:
            for col in ["L1_TAG", "L2_TAG", "L3_TAG", "L4_TAG"]:
                detail_data[col] = detail_data[col].fillna("")

            fig_sunburst = px.sunburst(
                detail_data,
                path=["L1_TAG", "L2_TAG", "L3_TAG", "L4_TAG"],
                values="QUERY_COUNT",
                color="QUERY_COUNT",
                color_continuous_scale="Blues",
            )
            fig_sunburst.update_layout(height=600)
            st.plotly_chart(fig_sunburst, use_container_width=True)
        else:
            st.info("Not enough detail data for sunburst visualization.")

    with st.expander("View Raw Data"):
        st.dataframe(df, use_container_width=True, hide_index=True)
