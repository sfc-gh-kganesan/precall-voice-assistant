"""
UI components for the Feedback application.
Pure render functions that dispatch actions for state changes.
"""

import pandas as pd
import streamlit as st
from config import LLM_MODELS, config
from snowflake.snowpark import Session
from store import (
    SetCarouselIndexAction,
    SetFeedbackChunkIndexAction,
    SetPlaygroundAgentResponseAction,
    SetPlaygroundChunkIndexAction,
    SetPlaygroundResultsAction,
    dispatch,
    get_store,
)

from data import (
    generate_combined_response,
    get_feedback_for_query,
    run_search,
    save_feedback,
    save_search,
)


def render_stars(rating: int) -> str:
    """Render star rating as unicode."""
    return "★" * rating + "☆" * (5 - rating)


def render_carousel_nav(
    total_items: int,
    session_key: str,
    index_action_class,
    current_index: int,
    item_labels: list[str] | None = None,
    label_prefix: str = "Item",
) -> int:
    """Render carousel navigation with prev/next buttons and jump-to selector."""
    if total_items == 0:
        return 0

    current_idx = min(current_index, total_items - 1)

    col1, col2, col3, col4 = st.columns([1, 1, 2, 4])

    with col1:
        if st.button("← Prev", disabled=current_idx == 0, use_container_width=True, key=f"{session_key}_prev"):
            dispatch(index_action_class(index=current_idx - 1))
            st.rerun()

    with col2:
        if st.button("Next →", disabled=current_idx >= total_items - 1, use_container_width=True, key=f"{session_key}_next"):
            dispatch(index_action_class(index=current_idx + 1))
            st.rerun()

    with col3:
        st.container(height=42, border=False).markdown(f"**{label_prefix} {current_idx + 1} of {total_items}**")

    with col4:
        labels = item_labels if item_labels and len(item_labels) == total_items else [f"{i + 1}" for i in range(total_items)]
        # Sync selectbox state with store before rendering
        jump_key = f"{session_key}_jump"
        if st.session_state.get(jump_key) != current_idx:
            st.session_state[jump_key] = current_idx
        selected = st.selectbox(
            "Jump to",
            range(total_items),
            format_func=lambda x: labels[x],
            key=jump_key,
            label_visibility="collapsed",
        )
        if selected != current_idx:
            dispatch(index_action_class(index=selected))
            st.rerun()

    return current_idx


@st.fragment
def render_feedback_form(session: Session, search_id: int, row_index: int, prefix: str = "feedback", label: str = "Rate This Chunk") -> None:
    """Render feedback form for a search result."""
    form_key = f"{prefix}_form_{search_id}_{row_index}"

    with st.form(key=form_key):
        st.markdown(f"**{label}**")
        rating = st.feedback("stars", key=f"{prefix}_rating_{search_id}_{row_index}")
        feedback = st.text_area(
            "Additional Comments",
            placeholder="I wished this came back with...",
            key=f"{prefix}_text_{search_id}_{row_index}",
            height=100,
            help="Describe what's missing or how this could better address the query.",
        )

        submitted = st.form_submit_button("Save Feedback")

        if submitted:
            if rating is None:
                st.warning("Please provide a star rating.")
            else:
                adjusted_rating = rating + config.RATING_ADJUSTMENT
                save_feedback(session, search_id, adjusted_rating, feedback or "")
                st.success("Feedback saved!")


def render_existing_feedback(session: Session, query_id: int) -> None:
    """Render existing feedback for a query."""
    feedback_df = get_feedback_for_query(session, query_id)

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


def render_chunk_card(
    session: Session,
    row: pd.Series,
    idx: int,
    total_chunks: int,
    search_id: int,
    query: str,
    prefix: str = "feedback",
) -> None:
    """Render a single chunk with content and feedback form."""
    st.caption(f"Query: {query}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Chunk Content**")
        st.info(row["CHUNK_TEXT"])
        col_a, col_b = st.columns(2)
        col_a.metric("Cosine Similarity", f"{row['COSINE_SIMILARITY']:.3f}")
        col_b.metric("Text Match", f"{row['TEXT_MATCH']:.3f}")

    with col2:
        render_feedback_form(session, search_id, idx, prefix=prefix, label="Rate This Chunk")


@st.fragment
def render_feedback_carousel(session: Session, source_df: pd.DataFrame) -> None:
    """Render the feedback carousel for reviewing search results."""
    grouped = list(source_df.groupby("INPUT_QUERY", sort=False))
    total_queries = len(grouped)

    if total_queries == 0:
        st.info("No queries to display.")
        return

    store = get_store()
    query_labels = [f"{i + 1}: {g[0][:40]}..." if len(str(g[0])) > 40 else f"{i + 1}: {g[0]}" for i, g in enumerate(grouped)]

    # Query-level carousel
    st.markdown("#### Navigate Queries")
    current_query_idx = render_carousel_nav(
        total_items=total_queries,
        session_key="feedback_query_carousel",
        index_action_class=SetCarouselIndexAction,
        current_index=store.carousel_index,
        item_labels=query_labels,
        label_prefix="Query",
    )

    st.divider()

    # Get current query data
    input_query, group_data = grouped[current_query_idx]
    row0 = group_data.iloc[0]
    search_id = row0.get("SEARCH_ID")
    prefix = row0.get("INPUT_TYPE", "feedback").lower().replace(" ", "_")
    total_chunks = len(group_data)

    st.subheader(input_query)

    # Chunk-level carousel
    st.markdown("#### Navigate Chunks")
    chunk_labels = [f"Chunk {i + 1}" for i in range(total_chunks)]
    current_chunk_idx = render_carousel_nav(
        total_items=total_chunks,
        session_key="feedback_chunk_carousel",
        index_action_class=SetFeedbackChunkIndexAction,
        current_index=store.feedback_chunk_index,
        item_labels=chunk_labels,
        label_prefix="Chunk",
    )

    st.divider()

    # Display current chunk
    current_row = group_data.iloc[current_chunk_idx]
    render_chunk_card(
        session,
        current_row,
        current_chunk_idx + 1,
        total_chunks,
        search_id,
        input_query,
        prefix=prefix,
    )

    # Existing feedback section
    st.divider()
    with st.expander("Existing Feedback", expanded=False):
        render_existing_feedback(session, search_id)


# ============================================================================
# Playground Tab Components
# ============================================================================


def render_playground_tab(session: Session) -> None:
    """Render the search playground tab."""
    st.header("Search Playground")
    st.caption("Test queries against your knowledge base and provide feedback on results.")

    # Settings
    with st.expander("Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            num_results = st.slider(
                "Number of results",
                min_value=1,
                max_value=10,
                value=5,
                key="playground_num_results",
            )
        with col2:
            st.selectbox(
                "LLM Model",
                options=list(LLM_MODELS),
                index=1,
                key="playground_llm_model",
            )

    # Search input
    query = st.text_input("Search", key="playground_search")

    if st.button("Search", key="playground_search_btn", type="primary") and query:
        with st.spinner("Searching..."):
            record, results = run_search(session, query, limit=num_results)
            search_id = save_search(session, record)
            dispatch(SetPlaygroundResultsAction(query=query, search_id=search_id, results=results))
            dispatch(SetPlaygroundAgentResponseAction(response=None))
        st.rerun()

    # Get fresh store state
    store = get_store()

    # Show results if available
    if not store.playground_results:
        return

    st.divider()

    # Mode tabs instead of radio buttons
    tab_agent, tab_chunks = st.tabs(["Agent Response", "Individual Chunks"])

    with tab_agent:
        _render_playground_agent_mode(session)

    with tab_chunks:
        _render_playground_chunks_mode(session)


def _render_playground_agent_mode(session: Session) -> None:
    """Render the agent response mode - combined response using all chunks."""
    store = get_store()
    llm_model = st.session_state.get("playground_llm_model", "llama3.1-70b")

    st.subheader(f"Results for: {store.playground_query}")

    # Generate combined response if not cached
    if store.playground_agent_response is None:
        with st.spinner("Generating agent response..."):
            response = generate_combined_response(
                session,
                store.playground_results,
                store.playground_query,
                model=llm_model,
            )
            dispatch(SetPlaygroundAgentResponseAction(response=response))
        st.rerun()

    # Display agent response
    st.markdown("### Agent Response")
    st.write(store.playground_agent_response)

    # Expandable section for retrieved chunks
    with st.expander(f"Retrieved Chunks ({len(store.playground_results)})", expanded=False):
        for idx, result in enumerate(store.playground_results, 1):
            st.markdown(f"**Chunk {idx}**")
            col_a, col_b = st.columns(2)
            col_a.metric("Cosine Similarity", f"{result['@scores']['cosine_similarity']:.3f}")
            col_b.metric("Text Match", f"{result['@scores']['text_match']:.3f}")
            st.info(result["CHUNK_TEXT"])
            if idx < len(store.playground_results):
                st.divider()

    # Feedback form for overall response
    st.divider()
    if store.playground_search_id is not None:
        render_feedback_form(
            session,
            store.playground_search_id,
            0,
            prefix="playground_agent",
            label="Rate This Response",
        )
    else:
        st.error("Could not retrieve search ID for feedback.")


def _render_playground_chunks_mode(session: Session) -> None:
    """Render the individual chunks mode with carousel navigation."""
    store = get_store()
    results = store.playground_results
    total_chunks = len(results)

    if total_chunks == 0:
        st.info("No chunks to display.")
        return

    # Carousel navigation
    chunk_labels = [f"Chunk {i + 1}" for i in range(total_chunks)]
    current_idx = render_carousel_nav(
        total_items=total_chunks,
        session_key="playground_chunks",
        index_action_class=SetPlaygroundChunkIndexAction,
        current_index=store.playground_chunk_index,
        item_labels=chunk_labels,
        label_prefix="Chunk",
    )

    st.divider()

    # Display current chunk
    result = results[current_idx]

    st.markdown(f"### Chunk {current_idx + 1} of {total_chunks}")
    st.caption(f"Query: {store.playground_query}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Chunk Content**")
        st.info(result["CHUNK_TEXT"])
        col_a, col_b = st.columns(2)
        col_a.metric("Cosine Similarity", f"{result['@scores']['cosine_similarity']:.3f}")
        col_b.metric("Text Match", f"{result['@scores']['text_match']:.3f}")

    with col2:
        if store.playground_search_id is not None:
            render_feedback_form(
                session,
                store.playground_search_id,
                current_idx + 1,
                prefix="playground_chunk",
                label="Rate This Chunk",
            )
        else:
            st.error("Could not retrieve search ID for feedback.")


# ============================================================================
# Feedback Tab Components
# ============================================================================


def render_feedback_tab(session: Session, source_df: pd.DataFrame, feedback_counts: pd.DataFrame) -> None:
    """Render the feedback review tab."""
    st.header("Search Results Review")
    st.caption("Review search results and provide feedback on retrieval quality.")

    with st.expander("How to provide feedback", expanded=False, icon=":material/help:"):
        st.markdown("""
**What you're evaluating:** Each query returns one or more *chunks* from your knowledge base.

**Rating guide:**
- ⭐ Poor - Chunk is irrelevant or misleading
- ⭐⭐ Below average - Chunk is tangentially related but not helpful
- ⭐⭐⭐ Average - Chunk contains some useful information
- ⭐⭐⭐⭐ Good - Chunk is relevant and helpful
- ⭐⭐⭐⭐⭐ Excellent - Chunk directly answers the query
        """)

    if source_df.empty:
        st.info("No search results available for review.")
        return

    # Merge feedback counts
    if not feedback_counts.empty:
        source_df = source_df.merge(feedback_counts, on="SEARCH_ID", how="left")
        source_df["FEEDBACK_COUNT"] = source_df["FEEDBACK_COUNT"].fillna(0).astype(int)
    else:
        source_df["FEEDBACK_COUNT"] = 0

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    total_queries = source_df["INPUT_QUERY"].nunique()
    total_responses = len(source_df)
    reviewed_queries = source_df[source_df["FEEDBACK_COUNT"] > 0]["INPUT_QUERY"].nunique()
    review_pct = (reviewed_queries / total_queries * 100) if total_queries > 0 else 0

    col1.metric("Queries", total_queries)
    col2.metric("Responses", total_responses)
    col3.metric("Reviewed", reviewed_queries)
    col4.metric("Coverage", f"{review_pct:.1f}%")

    st.divider()

    render_feedback_carousel(session, source_df)
