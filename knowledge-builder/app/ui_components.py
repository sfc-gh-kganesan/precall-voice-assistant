from collections.abc import Callable
from datetime import datetime

import pandas as pd
import streamlit as st
from config import db_config, ui_config
from data_operations import SnowflakeDataOperations
from ui_utils import render_stars


def get_metrics(df: pd.DataFrame) -> tuple[int, int, float, float]:
    return (
        df["INPUT_QUERY"].nunique(),
        df.shape[0],
        df["COSINE_SIMILARITY"].mean().round(3),
        df["TEXT_MATCH"].mean().round(3),
    )


def render_stats_tab(results_df: pd.DataFrame) -> None:
    st.header("Stats")

    with st.expander("Debug: View Raw Data Sample"):
        st.dataframe(results_df.head(), width="stretch")

    col1, col2, col3, col4 = st.columns(4)
    metrics = get_metrics(results_df)
    col1.metric("Input Queries", metrics[0])
    col2.metric("Responses", str(metrics[1]))
    col3.metric("Average Cosine Similarity", metrics[2])
    col4.metric("Average Text Match", metrics[3])


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

    st.markdown(f"### Response {idx} of {num_responses}")

    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown("**Retrieved Response**")
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
        st.markdown("**User Evaluation**")
        rating = st.feedback("stars", key=f"{prefix}_rating_{query_id}_{row_index}")
        feedback = st.text_area(
            "Additional Comments",
            placeholder=ui_config.feedback_placeholder,
            key=f"{prefix}_text_{query_id}_{row_index}",
            height=ui_config.feedback_textarea_height,
        )

        submitted = st.form_submit_button("Save")

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
        if response_key not in st.session_state:
            st.session_state[response_key] = 0

        st.session_state[response_key] = min(st.session_state[response_key], num_responses - 1)
        current_response_idx = st.session_state[response_key]

        r_col1, r_col2, r_col3 = st.columns([1, 1, 4])

        with r_col1:
            if st.button("◀ Prev", disabled=current_response_idx == 0, key=f"{prefix}_{query_id}_prev_resp", use_container_width=True):
                st.session_state[response_key] -= 1
                st.rerun()

        with r_col2:
            if st.button("Next ▶", disabled=current_response_idx >= num_responses - 1, key=f"{prefix}_{query_id}_next_resp", use_container_width=True):
                st.session_state[response_key] += 1
                st.rerun()

        with r_col3:
            st.container(height=42, border=False).markdown(f"**Response {current_response_idx + 1} of {num_responses}**")

        row_index = group_data.index[current_response_idx]
        row = group_data.iloc[current_response_idx]
        render_response_card(row, current_response_idx + 1, num_responses, query_id, input_query, row_index, data_ops, prefix=prefix, on_feedback_submit=on_feedback_submit)

    st.divider()
    st.markdown("**Existing Feedback**")
    render_existing_feedback(data_ops, query_id)


def render_playground_tab(data_ops: SnowflakeDataOperations) -> None:
    st.header("Search Playground")
    st.caption("Test ad-hoc queries against your knowledge base and provide feedback on results.")

    query = st.text_input("Search", key="playground_search")

    if st.button("Search", key="playground_search_btn") and query:
        with st.spinner("Searching..."):
            search_id, results = data_ops.execute_playground_search(query)

        st.subheader(f"Results for: {query}")
        results_df = data_ops.generate_llm_responses(results, query)

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
    st.header("Feedback Review")

    selected_types = st.multiselect(
        "Source",
        options=input_types,
        default=input_types[:1] if input_types else [],
        key="feedback_type_selector",
    )

    if not selected_types:
        st.info("Select at least one source type to review feedback.")
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
    col4.metric("Coverage", f"{review_pct:.0f}%")

    st.divider()

    group_col = "INPUT_QUERY" if "INPUT_QUERY" in source_df.columns else "SEARCH_ID"

    if group_col not in source_df.columns:
        group_col = source_df.columns[0]

    grouped = list(source_df.groupby(group_col, sort=False))
    total_queries = len(grouped)

    if "carousel_index" not in st.session_state:
        st.session_state.carousel_index = 0

    st.session_state.carousel_index = min(st.session_state.carousel_index, total_queries - 1)
    current_idx = st.session_state.carousel_index

    col1, col2, col3, col4 = st.columns([1, 1, 2, 2])

    with col1:
        if st.button("← Previous", disabled=current_idx == 0, use_container_width=True):
            st.session_state.carousel_index -= 1
            st.rerun()

    with col2:
        if st.button("Next →", disabled=current_idx >= total_queries - 1, use_container_width=True):
            st.session_state.carousel_index += 1
            st.rerun()

    with col3:
        st.container(height=42, border=False).markdown(f"**Query {current_idx + 1} of {total_queries}**")

    with col4:
        query_labels = [f"{i + 1}: {g[0][:40]}..." if len(str(g[0])) > 40 else f"{i + 1}: {g[0]}" for i, g in enumerate(grouped)]
        selected = st.selectbox(
            "Jump to",
            range(total_queries),
            index=current_idx,
            format_func=lambda x: query_labels[x],
            key="query_jump",
            label_visibility="collapsed",
        )
        if selected != current_idx:
            st.session_state.carousel_index = selected
            st.rerun()

    st.divider()

    _, group_data = grouped[current_idx]
    row0 = group_data.iloc[0]

    query_id = row0.get("SEARCH_ID")
    input_query = row0["INPUT_QUERY"]
    resolution_notes = row0.get("SUGGESTED_RESOLUTION")
    prefix = row0.get("_SOURCE_TYPE", "feedback").lower().replace(" ", "_")

    render_carousel_query(group_data, query_id, input_query, data_ops, prefix, resolution_notes, on_feedback_submit=on_feedback_submit)
