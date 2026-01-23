from collections.abc import Callable
from datetime import datetime

import pandas as pd
import streamlit as st
from config import LLM_MODELS, db_config, ui_config
from data_operations import SnowflakeDataOperations
from ui_utils import render_carousel_nav, render_stars


def render_response_card(
    row: pd.Series,
    idx: int,
    num_responses: int,
    query_id: int,
    input_query: str,
    row_index: int,
    data_ops: SnowflakeDataOperations,
    prefix: str = "baseline",
    on_feedback_submit: Callable = None,
) -> None:
    chunk_text = row["CHUNK_TEXT"]
    cosine_similarity = row["COSINE_SIMILARITY"]
    text_match = row["TEXT_MATCH"]

    st.markdown(f"### Retrieved Chunk {idx} of {num_responses}")

    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown("**Chunk Content**")
        st.info(chunk_text)
        col_a, col_b = st.columns(2)
        col_a.metric("Cosine Similarity", f"{cosine_similarity:.3f}")
        col_b.metric("Text Match", f"{text_match:.3f}")

    with c2:
        feedback_form(query_id, row_index, data_ops, prefix=prefix, on_submit=on_feedback_submit)

    if idx < num_responses:
        st.divider()


@st.fragment
def feedback_form(
    query_id: int,
    row_index: int,
    data_ops: SnowflakeDataOperations,
    prefix: str = "baseline",
    on_submit: Callable = None,
) -> None:
    form_key = f"{prefix}_form_{query_id}_{row_index}"

    with st.form(key=form_key):
        st.markdown("**Rate This Chunk**")
        st.caption("How well does this retrieved chunk answer the query above?")
        rating = st.feedback("stars", key=f"{prefix}_rating_{query_id}_{row_index}")
        feedback = st.text_area(
            "Additional Comments",
            placeholder=ui_config.feedback_placeholder,
            key=f"{prefix}_text_{query_id}_{row_index}",
            height=ui_config.feedback_textarea_height,
            help="Describe what's missing or how this chunk could better address the query.",
        )

        submitted = st.form_submit_button("Save Feedback")

        if submitted:
            if rating is None:
                st.warning("Please provide a star rating.")
            else:
                current_user = getattr(st.user, "email", None) or getattr(st.user, "name", None) or data_ops._session.get_current_user()
                feedback_data = [
                    [
                        int(query_id),
                        feedback.strip(),
                        rating + ui_config.rating_adjustment,
                        current_user,
                        datetime.now(),
                    ]
                ]

                data_ops.save_feedback(feedback_data)
                if on_submit:
                    on_submit()
                st.success(f"Feedback saved to {db_config.target_table}!")


def render_existing_feedback(data_ops: SnowflakeDataOperations, query_id: int) -> None:
    feedback_df = data_ops.get_feedback_for_query(query_id)

    if feedback_df.empty:
        st.caption("No feedback submitted yet.")
        return

    avg_rating = feedback_df["USER_RATING"].mean()
    st.metric("Average Rating", f"{avg_rating:.2f} / 5", delta=f"{len(feedback_df)} reviews")

    for _, row in feedback_df.iterrows():
        user = row["CREATED_BY"] or "Anonymous"
        rating = int(row["USER_RATING"]) if pd.notna(row["USER_RATING"]) else 0
        comment = row["USER_FEEDBACK"] or ""
        created = row["CREATED_ON"]

        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{user}** {render_stars(rating)}")
            c2.caption(created.strftime("%Y-%m-%d %H:%M") if pd.notna(created) else "")
            if comment:
                st.caption(comment)


def render_carousel_query(
    group_data: pd.DataFrame,
    query_id: int,
    input_query: str,
    data_ops: SnowflakeDataOperations,
    prefix: str,
    resolution_notes: str = None,
    on_feedback_submit: Callable = None,
) -> None:
    st.subheader(input_query)

    if resolution_notes:
        st.info(f"**Resolution Notes:** {resolution_notes}")

    num_responses = len(group_data)

    if num_responses <= 1:
        for idx, (row_index, row) in enumerate(group_data.iterrows(), 1):
            render_response_card(row, idx, num_responses, query_id, input_query, row_index, data_ops, prefix=prefix, on_feedback_submit=on_feedback_submit)
    else:
        response_key = f"{prefix}_{query_id}_response_idx"
        current_idx = render_carousel_nav(
            total_items=num_responses,
            session_key=response_key,
            label_prefix="Chunk",
        )

        row_index = group_data.index[current_idx]
        row = group_data.iloc[current_idx]
        render_response_card(row, current_idx + 1, num_responses, query_id, input_query, row_index, data_ops, prefix=prefix, on_feedback_submit=on_feedback_submit)

    st.divider()
    st.markdown("**Existing Feedback**")
    render_existing_feedback(data_ops, query_id)


def render_playground_tab(data_ops: SnowflakeDataOperations) -> None:
    st.header("Search Playground")
    st.caption("Test adhoc queries against your knowledge base and provide feedback on results.")

    with st.expander("Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            num_results = st.slider(
                "Number of results",
                min_value=1,
                max_value=10,
                value=1,
                key="playground_num_results",
            )
        with col2:
            llm_model = st.selectbox(
                "LLM Model",
                options=list(LLM_MODELS),
                index=1,
                key="playground_llm_model",
            )

    query = st.text_input("Search", key="playground_search")

    if st.button("Search", key="playground_search_btn") and query:
        with st.spinner("Searching..."):
            search_id, results = data_ops.execute_playground_search(query, limit=num_results)

        st.session_state["playground_last_search"] = {
            "query": query,
            "search_id": search_id,
            "results": results,
            "llm_model": llm_model,
        }

    _render_playground_results(data_ops)


@st.fragment
def _render_playground_results(data_ops: SnowflakeDataOperations) -> None:
    """Render playground search results as a fragment to prevent ghosting."""
    if "playground_last_search" not in st.session_state:
        return

    search_data = st.session_state["playground_last_search"]
    query = search_data["query"]
    search_id = search_data["search_id"]
    results = search_data["results"]
    llm_model = search_data["llm_model"]

    if not results:
        return

    st.subheader(f"Results for: {query}")
    results_df = data_ops.generate_llm_responses(results, query, model=llm_model)

    for idx, (row, result_dict) in enumerate(zip(results_df.itertuples(), results, strict=False), 1):
        st.markdown(f"### Result {idx}")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("**Chunk Details**")
            col_a, col_b = st.columns(2)
            col_a.metric("Text Match", f"{result_dict['@scores']['text_match']:.3f}")
            col_b.metric(
                "Cosine Similarity",
                f"{result_dict['@scores']['cosine_similarity']:.3f}",
            )
            st.info(result_dict["CHUNK_TEXT"])

        with col2:
            st.markdown("**Agent Response**")
            st.write(row.agent_response)

        st.markdown("**Feedback**")
        if search_id is not None:
            feedback_form(search_id, idx, data_ops, prefix="playground")
        else:
            st.error("Could not retrieve search ID for feedback.")

        if idx < len(results):
            st.divider()


def render_feedback_tab(
    data_ops: SnowflakeDataOperations,
    input_types: list[str],
    load_results_fn: Callable,
    on_feedback_submit: Callable = None,
) -> None:
    st.header("Search Results Review")
    st.caption("Review search results by query type and provide feedback on retrieval quality.")

    with st.expander("How to provide feedback", expanded=False, icon=":material/help:"):
        st.markdown("""
**What you're evaluating:** Each query returns one or more *chunks* from your knowledge base.
A chunk is a segment of text retrieved by the Cortex Search service based on semantic similarity to the query.

**Your feedback helps answer:**
- Does this chunk contain relevant information for the query?
- Would this chunk help someone find an answer?
- Is this the right content, or should a different article/section be returned?

**Rating guide:**
- :star: Poor - Chunk is irrelevant or misleading
- :star::star: Below average - Chunk is tangentially related but not helpful
- :star::star::star: Average - Chunk contains some useful information
- :star::star::star::star: Good - Chunk is relevant and helpful
- :star::star::star::star::star: Excellent - Chunk directly answers the query
        """)

    selected_types = st.multiselect(
        "Query Type",
        options=input_types,
        default=input_types[:1] if input_types else [],
        key="feedback_type_selector",
    )

    if not selected_types:
        st.info("Select at least one query type to review results.")
        return

    frames = []
    for t in selected_types:
        df = load_results_fn(data_ops, t)
        if not df.empty:
            df = df.copy()
            df["_SOURCE_TYPE"] = t
            frames.append(df)

    if not frames:
        st.info("No results for selected types.")
        return

    source_df = pd.concat(frames, ignore_index=True)

    feedback_counts = data_ops.get_feedback_counts()
    if not feedback_counts.empty:
        source_df = source_df.merge(feedback_counts, on="SEARCH_ID", how="left")
        source_df["FEEDBACK_COUNT"] = source_df["FEEDBACK_COUNT"].fillna(0).astype(int)
    else:
        source_df["FEEDBACK_COUNT"] = 0

    col1, col2, col3, col4 = st.columns(4)
    total_queries = source_df["INPUT_QUERY"].nunique()
    total_responses = len(source_df)
    reviewed_queries = source_df[source_df["FEEDBACK_COUNT"] > 0]["INPUT_QUERY"].nunique()
    review_pct = (reviewed_queries / total_queries * 100) if total_queries > 0 else 0

    col1.metric("Queries", total_queries)
    col2.metric("Responses", total_responses)
    col3.metric("Reviewed", reviewed_queries)
    col4.metric("Coverage", f"{review_pct:.3f}%")

    st.divider()

    render_carousel(source_df, data_ops, on_feedback_submit)


@st.fragment
def render_carousel(
    source_df: pd.DataFrame,
    data_ops: SnowflakeDataOperations,
    on_feedback_submit: Callable = None,
) -> None:
    """Render the carousel as a fragment for faster navigation."""
    group_col = "INPUT_QUERY" if "INPUT_QUERY" in source_df.columns else "SEARCH_ID"

    if group_col not in source_df.columns:
        group_col = source_df.columns[0]

    grouped = list(source_df.groupby(group_col, sort=False))
    total_queries = len(grouped)

    if total_queries == 0:
        st.info("No queries to display.")
        return

    query_labels = [f"{i + 1}: {g[0][:40]}..." if len(str(g[0])) > 40 else f"{i + 1}: {g[0]}" for i, g in enumerate(grouped)]

    current_idx = render_carousel_nav(
        total_items=total_queries,
        session_key="carousel_index",
        item_labels=query_labels,
        label_prefix="Query",
    )

    st.divider()

    _, group_data = grouped[current_idx]
    row0 = group_data.iloc[0]

    query_id = row0.get("SEARCH_ID")
    input_query = row0["INPUT_QUERY"]
    resolution_notes = row0.get("SUGGESTED_RESOLUTION")
    prefix = row0.get("_SOURCE_TYPE", "feedback").lower().replace(" ", "_")

    render_carousel_query(group_data, query_id, input_query, data_ops, prefix, resolution_notes, on_feedback_submit=on_feedback_submit)
