"""UI components for the Feedback application."""

import pandas as pd
import streamlit as st
from config import LLM_MODELS, config
from snowflake.snowpark import Session
from store import (
    SetCarouselIndexAction,
    SetFeedbackAgentResponseAction,
    SetFeedbackArticleIndexAction,
    SetFeedbackChunkIndexAction,
    SetPlaygroundAgentResponseAction,
    SetPlaygroundArticleIndexAction,
    SetPlaygroundChunkIndexAction,
    SetPlaygroundResultsAction,
    dispatch,
    get_store,
)

from data import (
    generate_combined_response,
    generate_feedback_agent_response,
    get_articles_for_chunks,
    get_evaluation_results,
    get_feedback_for_query,
    run_search,
    save_feedback,
    save_search,
)


def inject_app_styles() -> None:
    """Inject application CSS styles from external file."""
    from pathlib import Path

    css_path = Path(__file__).parent / "styles.css"
    css = css_path.read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


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
        if st.button("Prev", icon=":material/arrow_back:", disabled=current_idx == 0, use_container_width=True, key=f"{session_key}_prev"):
            dispatch(index_action_class(index=current_idx - 1))
            st.rerun()

    with col2:
        if st.button("Next", icon=":material/arrow_forward:", disabled=current_idx >= total_items - 1, use_container_width=True, key=f"{session_key}_next"):
            dispatch(index_action_class(index=current_idx + 1))
            st.rerun()

    with col3:
        st.container(height=42, border=False).markdown(f"**{label_prefix} {current_idx + 1} of {total_items}**")

    with col4:
        labels = item_labels if item_labels and len(item_labels) == total_items else [f"{i + 1}" for i in range(total_items)]
        jump_key = f"{session_key}_jump"
        selected = st.selectbox(
            "Jump to",
            range(total_items),
            index=current_idx,
            format_func=lambda x: labels[x],
            key=jump_key,
            label_visibility="collapsed",
        )
        if selected != current_idx:
            dispatch(index_action_class(index=selected))
            st.rerun()

    return current_idx


def render_chunk_thumbnails(
    group_data: pd.DataFrame,
    current_chunk_idx: int,
    feedback_counts: dict[int, int] | None = None,
    session_key: str = "feedback",
) -> int | None:
    """Render horizontal chunk thumbnail strip with clickable cards."""
    total_chunks = len(group_data)
    if total_chunks == 0:
        return None

    visible_chunks = min(total_chunks, 10)
    cols = st.columns(visible_chunks)

    clicked_idx = None
    for i, col in enumerate(cols):
        if i >= total_chunks:
            break

        row = group_data.iloc[i]
        chunk_text = row["CHUNK_TEXT"]
        preview = chunk_text[:120] + "..." if len(chunk_text) > 120 else chunk_text
        preview = preview.replace("<", "&lt;").replace(">", "&gt;")
        score = row.get("COSINE_SIMILARITY", 0)

        has_feedback = False
        if feedback_counts and row.get("SEARCH_ID") in feedback_counts:
            has_feedback = feedback_counts[row["SEARCH_ID"]] > 0

        is_active = i == current_chunk_idx
        active_class = " active" if is_active else ""
        badge_html = '<span class="chunk-thumb-badge">✓</span>' if has_feedback else ""

        with col:
            btn_key = f"{session_key}_thumb_{i}"
            st.markdown(
                f"""<div class="chunk-thumb{active_class}" data-btn="{btn_key}">
                    <div class="chunk-thumb-header">
                        <span class="chunk-thumb-num">#{i + 1}{badge_html}</span>
                        <span class="chunk-thumb-score">{score:.2f}</span>
                    </div>
                    <div class="chunk-thumb-preview">{preview}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            # Invisible button overlays the thumbnail for click handling
            if st.button("Select", key=btn_key, use_container_width=True, type="tertiary"):
                clicked_idx = i

    return clicked_idx


@st.fragment
def render_feedback_form(
    session: Session,
    search_id: int,
    row_index: int,
    prefix: str = "feedback",
    label: str = "Rate This Chunk",
    compact: bool = False,
    feedback_type: str = "CHUNK",
    chunk_index: int | None = None,
) -> None:
    """Render feedback form for a search result.

    Args:
        session: Snowpark session
        search_id: The search query ID
        row_index: Used for unique form keys
        prefix: Form key prefix
        label: Label for the rating section
        compact: Use compact layout
        feedback_type: 'CHUNK' or 'AGENT_RESPONSE'
        chunk_index: 0-based index of chunk (None for agent response)
    """
    form_key = f"{prefix}_form_{search_id}_{row_index}"
    submitted_key = f"{prefix}_submitted_{search_id}_{row_index}"

    # Check if feedback was just submitted
    if st.session_state.get(submitted_key):
        st.success("Thank you for your feedback! Your input helps us improve search quality.")
        if st.button("Submit another response", key=f"{prefix}_reset_{search_id}_{row_index}"):
            st.session_state[submitted_key] = False
            st.rerun()
        return

    # Rating guidance
    with st.expander("How to rate", expanded=False, icon=":material/help:"):
        st.markdown("""
**Star ratings:**
- ⭐ Poor — Not relevant to the query
- ⭐⭐ Fair — Tangentially related
- ⭐⭐⭐ Good — Somewhat relevant
- ⭐⭐⭐⭐ Very Good — Mostly answers the query
- ⭐⭐⭐⭐⭐ Excellent — Directly answers the query

**Comments (optional):** Describe what's missing, incorrect, or how the result could better address the query.
""")

    with st.form(key=form_key, border=False):
        if compact:
            col_label, col_stars = st.columns([2, 3])
            with col_label:
                st.markdown(f"**{label}**")
            with col_stars:
                rating = st.feedback("stars", key=f"{prefix}_rating_{search_id}_{row_index}")

            feedback = st.text_area(
                "Comment (optional)",
                placeholder="Describe what's missing or how this could be improved...",
                key=f"{prefix}_text_{search_id}_{row_index}",
                height=60,
                label_visibility="collapsed",
            )
            col_anon, col_submit = st.columns([3, 1.5])
            with col_anon:
                anonymous = st.checkbox("Submit anonymously", key=f"{prefix}_anon_{search_id}_{row_index}")
            with col_submit:
                submitted = st.form_submit_button("Save", use_container_width=True)
        else:
            st.markdown(f"**{label}**")
            rating = st.feedback("stars", key=f"{prefix}_rating_{search_id}_{row_index}")
            feedback = st.text_area(
                "Comment (optional)",
                placeholder="Describe what's missing or how this could be improved...",
                key=f"{prefix}_text_{search_id}_{row_index}",
                height=100,
            )
            anonymous = st.checkbox("Submit anonymously", key=f"{prefix}_anon_{search_id}_{row_index}")
            submitted = st.form_submit_button("Save Feedback")

        if submitted:
            if rating is None:
                st.warning("Please provide a star rating.")
            else:
                adjusted_rating = rating + config.RATING_ADJUSTMENT
                save_feedback(
                    session,
                    search_id,
                    adjusted_rating,
                    feedback or "",
                    feedback_type=feedback_type,
                    chunk_index=chunk_index,
                    anonymous=anonymous,
                )
                st.session_state[submitted_key] = True
                st.toast("Feedback saved!")
                st.rerun()


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
    evaluation: dict | None = None,
    chunk_index: int = 0,
) -> None:
    """Render a single chunk with content and feedback form."""
    chunk_text = str(row["CHUNK_TEXT"]).replace("<", "&lt;").replace(">", "&gt;")

    with st.container():
        st.markdown(
            f"""<div class="chunk-card">
                <div class="chunk-card-label">Chunk Content</div>
                <div class="chunk-card-content scrollable-chunk">{chunk_text}</div>
            </div>""",
            unsafe_allow_html=True,
        )

        if evaluation and evaluation.get("score") is not None:
            col_sim, col_match, col_rerank, col_rel = st.columns([1, 1, 1, 1])
            col_sim.metric("Similarity", f"{row['COSINE_SIMILARITY']:.3f}")
            col_match.metric("Text Match", f"{row['TEXT_MATCH']:.3f}")
            col_rerank.metric("Reranker", f"{row.get('RERANKER_SCORE', 0):.3f}")
            col_rel.metric("Context Relevance", f"{evaluation['score']:.2f}")

            if evaluation.get("reason"):
                with st.expander("Evaluation Reasoning", expanded=False, icon=":material/psychology:"):
                    st.caption(f"Model: {evaluation.get('model', 'Unknown')}")
                    st.write(evaluation["reason"])
        else:
            col_sim, col_match, col_rerank, col_spacer = st.columns([1, 1, 1, 1])
            col_sim.metric("Similarity", f"{row['COSINE_SIMILARITY']:.3f}")
            col_match.metric("Text Match", f"{row['TEXT_MATCH']:.3f}")
            col_rerank.metric("Reranker", f"{row.get('RERANKER_SCORE', 0):.3f}")
            st.caption("*Not evaluated*")

    render_feedback_form(session, search_id, idx, prefix=prefix, label="Rate this chunk", compact=True, chunk_index=chunk_index)


def render_articles_carousel(
    session: Session,
    chunk_texts: list[str],
    search_id: int,
    current_article_idx: int,
    index_action_class,
    prefix: str = "article",
) -> None:
    """Render articles in a carousel with navigation and rating."""
    if not chunk_texts:
        st.info("No chunks available to look up articles.")
        return

    articles = get_articles_for_chunks(session, tuple(chunk_texts))

    if not articles:
        st.warning("Could not find source articles for these chunks.")
        return

    total_articles = len(articles)
    current_idx = min(current_article_idx, total_articles - 1)

    st.caption(f"{total_articles} unique article(s) from {len(chunk_texts)} retrieved chunks")

    # Navigation
    if total_articles > 1:
        col_prev, col_status, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("Prev", icon=":material/chevron_left:", disabled=current_idx == 0, key=f"{prefix}_prev", use_container_width=True):
                dispatch(index_action_class(index=current_idx - 1))
                st.rerun()
        with col_status:
            st.markdown(f"<div style='text-align:center; padding-top:6px;'><b>Article {current_idx + 1} / {total_articles}</b></div>", unsafe_allow_html=True)
        with col_next:
            if st.button("Next", icon=":material/chevron_right:", disabled=current_idx >= total_articles - 1, key=f"{prefix}_next", use_container_width=True):
                dispatch(index_action_class(index=current_idx + 1))
                st.rerun()

    # Current article
    article = articles[current_idx]
    number = article.get("number", "Unknown")
    title = article.get("short_description", "")
    text = article.get("text", "")
    chunk_indices = article.get("chunk_indices", [])

    # Format chunk indices as 1-based for display
    chunk_labels = ", ".join(str(i + 1) for i in chunk_indices)

    # Escape HTML
    title_safe = str(title).replace("<", "&lt;").replace(">", "&gt;") if title else ""
    text_safe = str(text).replace("<", "&lt;").replace(">", "&gt;") if text else ""

    st.markdown(
        f"""<div class="article-card">
            <div class="article-card-label">Knowledge Article</div>
            <div class="article-card-header">
                <span class="article-card-number">{number}</span>
                <span class="article-card-title">{title_safe}</span>
            </div>
            <div class="article-card-chunks">From chunk(s): {chunk_labels}</div>
            <div class="article-card-content">{text_safe}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Rating form for this article
    render_feedback_form(
        session,
        search_id,
        row_index=current_idx,
        prefix=f"{prefix}_{number}",
        label="Rate This Article",
        compact=True,
        feedback_type="ARTICLE",
        chunk_index=current_idx,
    )


def _render_feedback_agent_tab(
    session: Session,
    search_id: int,
    group_data: pd.DataFrame,
    query: str,
    prefix: str = "feedback",
) -> None:
    """Render the agent response tab with on-demand generation."""
    store = get_store()

    # Check if we have a response for this search_id
    has_response = store.feedback_agent_response is not None and store.feedback_agent_response_search_id == search_id

    if not has_response:
        st.info("Click the button below to generate an agent response using all retrieved chunks.")
        if st.button("Generate Agent Response", type="primary", key=f"generate_agent_{search_id}"):
            with st.spinner("Generating agent response..."):
                response = generate_feedback_agent_response(session, group_data, query)
                dispatch(SetFeedbackAgentResponseAction(search_id=search_id, response=response))
            st.rerun()
        return

    response_safe = str(store.feedback_agent_response).replace("<", "&lt;").replace(">", "&gt;")

    st.markdown(
        f"""<div class="agent-response-card">
            <div class="agent-response-label">Agent Response</div>
            <div class="agent-response-content">{response_safe}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    render_feedback_form(
        session,
        search_id,
        row_index=0,
        prefix=f"{prefix}_agent",
        label="Rate This Response",
        compact=True,
        feedback_type="AGENT_RESPONSE",
        chunk_index=None,
    )


@st.fragment
def render_feedback_carousel(session: Session, source_df: pd.DataFrame, feedback_counts_df: pd.DataFrame | None = None) -> None:
    """
    Render the feedback carousel for reviewing search results.

    Layout hierarchy:
    1. Full Knowledge Article (most prominent)
    2. Agent Response with feedback form
    3. Retrieved Chunks (collapsible) with individual feedback
    """
    grouped = list(source_df.groupby("INPUT_QUERY", sort=False))
    total_queries = len(grouped)

    if total_queries == 0:
        st.info("No queries to display.")
        return

    store = get_store()

    feedback_counts_dict = {}
    if feedback_counts_df is not None and not feedback_counts_df.empty:
        for _, row in feedback_counts_df.iterrows():
            feedback_counts_dict[row["SEARCH_ID"]] = row["FEEDBACK_COUNT"]

    eval_df = get_evaluation_results(session)
    eval_dict = {}
    if not eval_df.empty:
        for _, row in eval_df.iterrows():
            eval_dict[row["SEARCH_ID"]] = {
                "score": row["CONTEXT_RELEVANCE_SCORE"],
                "reason": row["CONTEXT_RELEVANCE_REASON"],
                "model": row["EVALUATION_MODEL"],
            }

    query_labels = []
    for i, (query_text, group) in enumerate(grouped):
        truncated = f"{query_text[:40]}..." if len(str(query_text)) > 40 else query_text
        has_feedback = any(feedback_counts_dict.get(row["SEARCH_ID"], 0) > 0 for _, row in group.iterrows())
        status = "✓ " if has_feedback else ""
        query_labels.append(f"{status}{i + 1}. {truncated}")

    current_query_idx = min(store.carousel_index, total_queries - 1)
    input_query, group_data = grouped[current_query_idx]
    row0 = group_data.iloc[0]
    search_id = row0.get("SEARCH_ID")
    prefix = row0.get("INPUT_TYPE", "feedback").lower().replace(" ", "_")
    total_chunks = len(group_data)
    current_chunk_idx = min(store.feedback_chunk_index, total_chunks - 1) if total_chunks > 0 else 0

    # Query navigation (simplified - just query selector)
    col_query, col_spacer = st.columns([4, 1])
    with col_query:
        jump_key = "feedback_query_jump"
        selected_query = st.selectbox(
            "Query",
            range(total_queries),
            index=current_query_idx,
            format_func=lambda x: query_labels[x],
            key=jump_key,
            label_visibility="collapsed",
        )
        if selected_query != current_query_idx:
            dispatch(SetCarouselIndexAction(index=selected_query))
            dispatch(SetFeedbackChunkIndexAction(index=0))
            st.rerun()

    st.markdown(f"### {input_query}")

    # Get all chunk texts for article lookup
    all_chunk_texts = group_data["CHUNK_TEXT"].tolist()

    # ─────────────────────────────────────────────────────────────────
    # TABBED INTERFACE: Knowledge Feedback, Agent, Chunks
    # ─────────────────────────────────────────────────────────────────
    tab_knowledge, tab_agent, tab_chunks = st.tabs(["Knowledge Feedback", "Agent", "Chunks"])

    with tab_knowledge:
        render_articles_carousel(
            session,
            all_chunk_texts,
            search_id,
            current_article_idx=store.feedback_article_index,
            index_action_class=SetFeedbackArticleIndexAction,
            prefix="feedback_article",
        )

    with tab_agent:
        _render_feedback_agent_tab(
            session,
            search_id,
            group_data,
            input_query,
            prefix=prefix,
        )

    with tab_chunks:
        # Chunk thumbnails strip
        if total_chunks > 1:
            st.caption("Click a chunk to view details:")
            clicked = render_chunk_thumbnails(
                group_data,
                current_chunk_idx,
                feedback_counts=feedback_counts_dict,
            )
            if clicked is not None and clicked != current_chunk_idx:
                dispatch(SetFeedbackChunkIndexAction(index=clicked))
                st.rerun()

        # Chunk navigation
        if total_chunks > 1:
            col_prev, col_status, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("Prev", icon=":material/chevron_left:", disabled=current_chunk_idx == 0, key="chunk_prev", use_container_width=True):
                    dispatch(SetFeedbackChunkIndexAction(index=current_chunk_idx - 1))
                    st.rerun()
            with col_status:
                st.markdown(f"<div style='text-align:center; padding-top:6px;'><b>Chunk {current_chunk_idx + 1} / {total_chunks}</b></div>", unsafe_allow_html=True)
            with col_next:
                if st.button("Next", icon=":material/chevron_right:", disabled=current_chunk_idx >= total_chunks - 1, key="chunk_next", use_container_width=True):
                    dispatch(SetFeedbackChunkIndexAction(index=current_chunk_idx + 1))
                    st.rerun()

        # Current chunk details
        current_row = group_data.iloc[current_chunk_idx]
        evaluation_data = eval_dict.get(search_id)
        render_chunk_card(
            session,
            current_row,
            current_chunk_idx + 1,
            total_chunks,
            search_id,
            input_query,
            prefix=prefix,
            evaluation=evaluation_data,
            chunk_index=current_chunk_idx,
        )

    # Previous feedback section
    feedback_df = get_feedback_for_query(session, search_id)
    if not feedback_df.empty:
        avg = feedback_df["USER_RATING"].mean()
        count = len(feedback_df)
        with st.expander(f"Previous feedback ({count}) — avg {avg:.1f}/5", expanded=False, icon=":material/reviews:"):
            render_existing_feedback(session, search_id)


def render_playground_tab(session: Session) -> None:
    """Render the search playground tab."""
    st.header("Search Playground")
    st.caption("Test queries against your knowledge base and provide feedback on results.")

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

    query = st.text_input("Search", key="playground_search")

    if st.button("Search", key="playground_search_btn", type="primary") and query:
        with st.spinner("Searching..."):
            record, results = run_search(session, query, limit=num_results)
            search_id = save_search(session, record)
            dispatch(SetPlaygroundResultsAction(query=query, search_id=search_id, results=results))
            dispatch(SetPlaygroundAgentResponseAction(response=None))
        st.rerun()

    store = get_store()

    if not store.playground_results:
        return

    st.divider()

    tab_knowledge, tab_agent, tab_chunks = st.tabs(["Knowledge Feedback", "Agent", "Chunks"])

    with tab_knowledge:
        all_chunk_texts = [r.get("CHUNK_TEXT") for r in store.playground_results if r.get("CHUNK_TEXT")]
        render_articles_carousel(
            session,
            all_chunk_texts,
            store.playground_search_id,
            current_article_idx=store.playground_article_index,
            index_action_class=SetPlaygroundArticleIndexAction,
            prefix="playground_article",
        )

    with tab_agent:
        _render_playground_agent_mode(session)

    with tab_chunks:
        _render_playground_chunks_mode(session)


def _render_playground_agent_mode(session: Session) -> None:
    """Render the agent response mode - combined response using all chunks."""
    store = get_store()
    llm_model = st.session_state.get("playground_llm_model", "llama3.1-70b")

    st.subheader(f"Results for: {store.playground_query}")

    if store.playground_agent_response is None:
        st.info("Click the button below to generate an agent response using all retrieved chunks.")
        if st.button("Generate Agent Response", type="primary", key="generate_agent_btn"):
            with st.spinner("Generating agent response..."):
                response = generate_combined_response(
                    session,
                    store.playground_results,
                    store.playground_query,
                    model=llm_model,
                )
                dispatch(SetPlaygroundAgentResponseAction(response=response))
            st.rerun()
        return

    st.markdown("### Agent Response")
    st.write(store.playground_agent_response)

    with st.expander(f"Retrieved Chunks ({len(store.playground_results)})", expanded=False):
        for idx, result in enumerate(store.playground_results, 1):
            st.markdown(f"**Chunk {idx}**")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Cosine Similarity", f"{result['@scores']['cosine_similarity']:.3f}")
            col_b.metric("Text Match", f"{result['@scores']['text_match']:.3f}")
            col_c.metric("Reranker", f"{result['@scores'].get('reranker_score', 0):.3f}")
            st.info(result["CHUNK_TEXT"])
            if idx < len(store.playground_results):
                st.divider()

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

    result = results[current_idx]

    st.markdown(f"### Chunk {current_idx + 1} of {total_chunks}")
    st.caption(f"Query: {store.playground_query}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Chunk Content**")
        st.info(result["CHUNK_TEXT"])
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Cosine Similarity", f"{result['@scores']['cosine_similarity']:.3f}")
        col_b.metric("Text Match", f"{result['@scores']['text_match']:.3f}")
        col_c.metric("Reranker", f"{result['@scores'].get('reranker_score', 0):.3f}")

    with col2:
        if store.playground_search_id is not None:
            render_feedback_form(
                session,
                store.playground_search_id,
                current_idx + 1,
                prefix="playground_chunk",
                label="Rate This Chunk",
                feedback_type="CHUNK",
                chunk_index=current_idx,
            )
        else:
            st.error("Could not retrieve search ID for feedback.")


def render_feedback_tab(session: Session, source_df: pd.DataFrame, feedback_counts: pd.DataFrame) -> None:
    """Render the feedback review tab."""
    st.header("Search Results Review")

    if source_df.empty:
        st.info("No search results available for review.")
        return

    if not feedback_counts.empty:
        source_df = source_df.merge(feedback_counts, on="SEARCH_ID", how="left")
        source_df["FEEDBACK_COUNT"] = source_df["FEEDBACK_COUNT"].fillna(0).astype(int)
    else:
        source_df["FEEDBACK_COUNT"] = 0

    render_feedback_carousel(session, source_df, feedback_counts_df=feedback_counts)
