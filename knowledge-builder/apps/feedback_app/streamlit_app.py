import streamlit as st
from config import config

st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout="wide",
)

from components import inject_app_styles, render_feedback_tab, render_playground_tab  # noqa: E402
from snowflake.snowpark import Session
from store import InitializeFiltersAction, SetInputTypesAction, dispatch, get_store, init_store  # noqa: E402

from data import get_average_scores, get_context_relevance_distribution, get_evaluation_status, get_feedback_counts, get_feedback_summary, get_input_types, get_search_results, get_session  # noqa: E402


def _stat_box(value: str, label: str) -> str:
    """Generate HTML for a single stat box."""
    return f'<div class="stat-box"><div class="stat-value">{value}</div><div class="stat-label">{label}</div></div>'


def _render_stat_grid(boxes: list[str]) -> None:
    """Render a grid of stat boxes."""
    if boxes:
        st.markdown(f'<div class="stats-grid">{"".join(boxes)}</div>', unsafe_allow_html=True)


def _render_distribution(items: list[tuple[str, int]], total: int, title: str) -> None:
    """Render a labeled progress bar distribution."""
    if total == 0:
        return

    st.markdown(f"**{title}**")
    for label, count in items:
        pct = (count / total * 100) if total > 0 else 0
        col_label, col_bar, col_count = st.columns([2, 4, 1])
        with col_label:
            st.caption(label)
        with col_bar:
            st.progress(pct / 100)
        with col_count:
            st.caption(f"{count}")


def render_stats_panel(session: Session, selected_types: tuple[str, ...]) -> None:
    """Render statistics panel with tabbed sections."""
    avg_scores = get_average_scores(session, selected_types)
    relevance_dist = get_context_relevance_distribution(session, selected_types)
    eval_status = get_evaluation_status(session, selected_types)
    feedback_summary = get_feedback_summary(session, selected_types)

    with st.container(border=True):
        st.caption("Statistics")

        tab_search, tab_eval, tab_feedback = st.tabs(["Search", "Evaluation", "Feedback"])

        with tab_search:
            boxes = []
            if avg_scores.get("cosine_similarity") is not None:
                boxes.append(_stat_box(f"{avg_scores['cosine_similarity']:.3f}", "Avg Cosine"))
            if avg_scores.get("text_match") is not None:
                boxes.append(_stat_box(f"{avg_scores['text_match']:.3f}", "Avg Text Match"))
            if avg_scores.get("reranker_score") is not None:
                boxes.append(_stat_box(f"{avg_scores['reranker_score']:.3f}", "Avg Reranker"))

            if boxes:
                _render_stat_grid(boxes)
            else:
                st.caption("No search score data available.")

        with tab_eval:
            # Check if evaluations have been run
            has_eval_data = avg_scores.get("context_relevance") is not None
            type_word = "type" if len(selected_types) == 1 else "types"
            if not has_eval_data:
                st.info(f"No evaluations are available for the selected query {type_word}.")
            else:
                boxes = [_stat_box(f"{avg_scores['context_relevance']:.2f}", "Avg Context Relevance")]

                for input_type, counts in eval_status.items():
                    evaluated, total = counts["evaluated"], counts["total"]
                    pct = int(evaluated / total * 100) if total > 0 else 0
                    label = input_type.replace("_", " ").title()
                    boxes.append(_stat_box(f"{evaluated}/{total}", f"{label} ({pct}%)"))

                _render_stat_grid(boxes)

                if any(relevance_dist.values()):
                    total_evals = sum(relevance_dist.values())
                    items = [
                        ("0 - Not Relevant", relevance_dist["0"]),
                        ("0.33 - Partially Relevant", relevance_dist["1"]),
                        ("0.66 - Mostly Relevant", relevance_dist["2"]),
                        ("1.0 - Fully Relevant", relevance_dist["3"]),
                    ]
                    _render_distribution(items, total_evals, "Context Relevance Distribution")

        with tab_feedback:
            if feedback_summary["total_feedback"] == 0:
                st.info("Submit feedback on search results to see rating statistics.")
            else:
                boxes = [_stat_box(str(feedback_summary["total_feedback"]), "Total Feedback")]
                if feedback_summary["avg_rating"] is not None:
                    boxes.append(_stat_box(f"{feedback_summary['avg_rating']:.1f}/5", "Avg Rating"))

                _render_stat_grid(boxes)

                rating_dist = feedback_summary["rating_distribution"]
                items = [("\u2605" * stars, rating_dist[stars]) for stars in range(5, 0, -1)]
                _render_distribution(items, feedback_summary["total_feedback"], "Rating Distribution")


def main() -> None:
    inject_app_styles()

    st.title(config.PAGE_TITLE)
    st.markdown("Review Cortex Search retrieval quality, evaluation scores, and provide feedback.")
    st.caption(f"Connected to `{config.DATABASE}.{config.SCHEMA}` | Search Service: `{config.SEARCH_SERVICE}`")

    init_store()
    session = get_session()
    input_types = get_input_types(session)

    store = get_store()
    if not store.filters_initialized and input_types:
        dispatch(InitializeFiltersAction(default_input_types=tuple(input_types)))

    tab_feedback, tab_playground = st.tabs(["Feedback", "Playground"])

    with tab_feedback:
        selected_types = st.multiselect(
            "Query Types",
            options=input_types,
            default=list(store.selected_input_types) if store.selected_input_types else input_types,
            key="input_type_selector",
        )

        if set(selected_types) != set(store.selected_input_types):
            dispatch(SetInputTypesAction(input_types=tuple(selected_types)))
            st.cache_data.clear()
            st.rerun()

        if selected_types:
            selected_tuple = tuple(selected_types)
            render_stats_panel(session, selected_tuple)
            st.divider()

            source_df = get_search_results(session, selected_tuple)
            feedback_counts = get_feedback_counts(session)
            render_feedback_tab(session, source_df, feedback_counts)
        else:
            st.info("Select one or more query types to review results.")

    with tab_playground:
        render_playground_tab(session)


main()
