from datetime import datetime
from urllib.parse import unquote, urlparse

import altair as alt
import pandas as pd
import streamlit as st
from snowflake.snowpark import functions as F
from trulens.providers.cortex import Cortex
from ydata_profiling import ProfileReport

from app.data_operations import SnowflakeDataOperations
from config import db_config, eda_config, ui_config


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
        feedback_form(query_id, row_index, data_ops, prefix=prefix)

    if idx < num_responses:
        st.divider()


@st.fragment
def feedback_form(
    query_id: int,
    row_index: int,
    data_ops: SnowflakeDataOperations,
    prefix: str = "baseline",
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
                feedback_data = [
                    [
                        query_id,
                        feedback.strip(),
                        rating + ui_config.rating_adjustment,
                        data_ops._session.get_current_user(),
                        datetime.now(),
                    ]
                ]

                data_ops.save_feedback(feedback_data)
                st.success(f"Feedback saved to {db_config.target_table}!")


def profile_data(df: pd.DataFrame) -> str:
    profile = ProfileReport(df, title="Pandas Profiling Report", explorative=True)
    profile.config.html.use_local_assets = True
    profile.config.html.inline = True
    profile.config.html.navbar_show = False
    return profile.to_html()


def extract_domains_from_html(html_text: str) -> list:
    if not isinstance(html_text, str) or not html_text:
        return []

    urls = eda_config.href_pattern.findall(html_text)
    urls += eda_config.url_pattern.findall(html_text)

    domains = []
    for raw in urls:
        try:
            if not raw or len(raw) < 4:
                continue

            u = unquote(raw.strip())

            u_lower = u.lower()
            if u_lower.startswith("www."):
                u = "https://" + u
            elif not u_lower.startswith(("http://", "https://")):
                continue

            parsed = urlparse(u)
            domain = parsed.netloc.lower()

            if not domain or domain in ("server", "localhost"):
                continue

            domains.append(domain)
        except ValueError:
            continue

    return domains


def analyze_outbound_links(df: pd.DataFrame, text_col: str = "TEXT") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["DOMAIN", "COUNT", "DISTINCT_ARTICLES"])

    if "ARTICLE_ID" in df.columns:
        id_col = "ARTICLE_ID"
    elif "SYS_ID" in df.columns:
        id_col = "SYS_ID"
    else:
        df = df.reset_index()
        id_col = "index"

    processed_data = [(row_id, extract_domains_from_html(text)) for row_id, text in zip(df[id_col], df[text_col], strict=False)]

    temp_df = pd.DataFrame(processed_data, columns=["ARTICLE_ID", "DOMAIN"])
    exploded_df = temp_df.explode("DOMAIN")
    exploded_df = exploded_df.dropna(subset=["DOMAIN"])
    if exploded_df.empty:
        return pd.DataFrame(columns=["DOMAIN", "COUNT", "DISTINCT_ARTICLES"])
    result = (
        exploded_df.groupby("DOMAIN")
        .agg(
            COUNT=("DOMAIN", "size"),
            DISTINCT_ARTICLES=("ARTICLE_ID", "nunique"),
        )
        .reset_index()
        .sort_values("COUNT", ascending=False)
    )
    return result


def render_eda_tab(data_ops: SnowflakeDataOperations) -> None:
    st.header("EDA - Knowledge Base Analysis")
    st.markdown("Exploratory data analysis of the knowledge base.")

    try:
        kb_knowledge = data_ops.get_knowledge_data(db_config.kb_knowledge_table)
        describe_df = kb_knowledge.describe()
        numeric_df = kb_knowledge.select_dtypes(exclude=["object"])
        cat_df = kb_knowledge.select_dtypes(include=["object"])
        report_html = profile_data(numeric_df)

        numeric_tab, cat_tab, links_tab, image_links_tab = st.tabs(["Numeric", "Categorical", "Outbound Links", "Image Links"])

        with numeric_tab:
            st.dataframe(describe_df)
            st.components.v1.html(report_html, width=1000, height=550, scrolling=True)

        with cat_tab:
            st.dataframe(cat_df.head())

        with links_tab:
            st.subheader("Outbound Link Analysis (Knowledge Leakage)")
            st.caption("Extracting external domains from article HTML content.")

            link_summary = analyze_outbound_links(kb_knowledge, text_col="TEXT")

            if link_summary.empty:
                st.warning("No outbound links found in the dataset.")
            else:
                st.dataframe(link_summary)

                chart = (
                    alt.Chart(link_summary.head(20))
                    .mark_bar()
                    .encode(
                        x=alt.X("COUNT:Q", title="Number of References"),
                        y=alt.Y("DOMAIN:N", sort="-x", title="Domain"),
                        tooltip=["DOMAIN", "COUNT"],
                    )
                    .properties(title="Top 20 Outbound Domains Referenced")
                )
                st.altair_chart(chart, use_container_width=True)

                st.caption("Domains such as Confluence, Atlassian, or SharePoint often indicate knowledge stored outside official systems.")

        with image_links_tab:
            st.subheader("Image Link Analysis")
            st.caption("Categorized image sources from <img> tags (via ANALYZE_IMAGE_LINKS SPROC).")

            try:
                image_summary = data_ops.call_stored_procedure("ANALYZE_IMAGE_LINKS")

                if image_summary.empty:
                    st.warning("No image links found in the dataset.")
                else:
                    st.dataframe(image_summary, use_container_width=True)

                    chart = (
                        alt.Chart(image_summary.head(15))
                        .mark_bar()
                        .encode(
                            x=alt.X("COUNT:Q", title="Count"),
                            y=alt.Y("CATEGORY:N", sort="-x", title="Category"),
                            tooltip=["CATEGORY", "COUNT", "DISTINCT_ARTICLES"],
                        )
                        .properties(title="Image Source Categories")
                    )
                    st.altair_chart(chart, use_container_width=True)
            except Exception as e:
                st.warning(f"Image link analysis not available. Create ANALYZE_IMAGE_LINKS stored procedure to enable this feature.\n\nError: {str(e)}")

    except Exception as e:
        st.error(f"Error loading EDA data: {str(e)}")
        st.info(f"Make sure the {db_config.kb_knowledge_table} table exists and is accessible.")


def render_evaluation_tab(data_ops: SnowflakeDataOperations) -> None:
    st.header("LLM-As-A-Judge Evaluation")
    st.markdown("Evaluate golden pair search results using LLM-based feedback metrics.")

    try:
        feedback_options = st.multiselect(
            "Select evaluation metrics:",
            options=[
                "Answer Relevance",
                "Context Relevance",
                "Groundedness",
                "Comprehensiveness",
                "Harmfulness",
            ],
            default=["Answer Relevance", "Context Relevance", "Groundedness"],
            key="eval_metrics",
        )

        existing_results = data_ops.get_evaluation_results()

        should_run = False

        if not existing_results.empty:
            st.info(f"Found {len(existing_results)} existing evaluation results. Displaying saved results.")

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("Re-run Evaluation", key="rerun_eval_btn"):
                    should_run = True

            if not should_run:
                st.subheader("Saved Evaluation Results")

                existing_results.columns = existing_results.columns.str.lower()

                if "metrics" in existing_results.columns:
                    metrics_df = pd.json_normalize(existing_results["metrics"])
                    display_df = pd.concat(
                        [
                            existing_results[
                                [
                                    "query",
                                    "context",
                                    "answer",
                                    "created_by",
                                    "created_on",
                                ]
                            ],
                            metrics_df,
                        ],
                        axis=1,
                    )
                else:
                    display_df = existing_results

                st.subheader("Average Scores")
                cols = st.columns(len(feedback_options))
                for idx, metric in enumerate(feedback_options):
                    metric_key = metric.lower().replace(" ", "_")
                    if metric_key in display_df.columns:
                        avg_score = display_df[metric_key].mean()
                        cols[idx].metric(metric, f"{avg_score:.3f}")

                st.subheader("Detailed Results")
                display_cols = ["query"]
                for metric in feedback_options:
                    metric_key = metric.lower().replace(" ", "_")
                    if metric_key in display_df.columns:
                        display_cols.append(metric_key)

                st.dataframe(display_df[display_cols], use_container_width=True)

                for metric in feedback_options:
                    metric_key = metric.lower().replace(" ", "_")
                    if metric_key in display_df.columns:
                        chart = (
                            alt.Chart(display_df.reset_index())
                            .mark_bar()
                            .encode(
                                x=alt.X("index:O", title="Query Index"),
                                y=alt.Y(
                                    f"{metric_key}:Q",
                                    title=metric,
                                    scale=alt.Scale(domain=[0, 1]),
                                ),
                                tooltip=["query", metric_key],
                            )
                            .properties(title=f"{metric} Scores", height=300)
                        )
                        st.altair_chart(chart, use_container_width=True)

                if "reasons" in existing_results.columns:
                    st.subheader("Chain-of-Thought Reasoning (Saved)")
                    st.markdown("Expand to see detailed reasoning for each evaluation:")

                    for idx, row in existing_results.iterrows():
                        with st.expander(f"Query {idx + 1}: {row['query'][:100]}..."):
                            st.markdown(f"**Context:** {row['context'][:200]}...")
                            st.markdown(f"**Answer:** {row['answer'][:200]}...")
                            st.divider()

                            if row["reasons"]:
                                reasons_dict = row["reasons"]
                                for metric in feedback_options:
                                    metric_key = metric.lower().replace(" ", "_")

                                    if metric_key in display_df.columns:
                                        score = display_df.loc[idx, metric_key] if metric_key in display_df.columns else None
                                        if score is not None:
                                            st.markdown(f"**{metric}:** {score:.3f}")

                                        if metric_key in reasons_dict:
                                            reasons = reasons_dict[metric_key]
                                            if isinstance(reasons, dict):
                                                if "reasons" in reasons:
                                                    st.markdown(f"*Reasoning:* {reasons['reasons']}")
                                                elif "reason" in reasons:
                                                    st.markdown(f"*Reasoning:* {reasons['reason']}")
                                                else:
                                                    st.json(reasons)
                                        st.divider()

                return
        else:
            if st.button("Run Evaluation", key="run_eval_btn"):
                should_run = True

        if should_run:
            with st.spinner("Running evaluations with TruLens..."):
                baseline_df = data_ops.get_baseline_results()

                if baseline_df.empty:
                    st.warning("No baseline test data available for evaluation.")
                    return

                st.subheader("Baseline Results Evaluation")

                progress_bar = st.progress(0)
                progress_bar.progress(0.1)

                provider = Cortex(data_ops._session, model_engine="llama3.1-70b")

                eval_df = data_ops._session.create_dataframe(
                    baseline_df.head(10)[["INPUT_QUERY", "CHUNK_TEXT"]].values.tolist(),
                    schema=["query", "context"],
                )

                eval_df = eval_df.with_column(
                    "answer",
                    F.call_builtin(
                        "SNOWFLAKE.CORTEX.COMPLETE",
                        F.lit("llama3.1-70b"),
                        F.prompt(
                            "Context: {0}\n\nQuestion: {1}\n\nPlease provide a helpful and accurate answer based on the context provided.",
                            F.col("context"),
                            F.col("query"),
                        ),
                    ),
                )

                progress_bar.progress(0.3)
                eval_results_df = eval_df.to_pandas()
                eval_results_df.columns = eval_results_df.columns.str.lower()

                total_metrics = len(feedback_options)
                for idx, metric in enumerate(feedback_options):
                    metric_key = metric.lower().replace(" ", "_")

                    st.text(f"Evaluating {metric}...")

                    scores = []
                    reasons_list = []

                    for _, row in eval_results_df.iterrows():
                        try:
                            if metric == "Answer Relevance":
                                score, reasons = provider.relevance_with_cot_reasons(prompt=row["query"], response=row["answer"], temperature=0.0)
                            elif metric == "Context Relevance":
                                score, reasons = provider.context_relevance_with_cot_reasons(question=row["query"], context=row["context"], temperature=0.0)
                            elif metric == "Groundedness":
                                score, reasons = provider.groundedness_measure_with_cot_reasons(source=row["context"], statement=row["answer"], temperature=0.0)
                            elif metric == "Comprehensiveness":
                                system_prompt = "Rate how comprehensive this answer is for the given question. Consider whether it covers all important aspects and provides sufficient detail. Provide a score between 0 and 1, where 0 is not comprehensive at all and 1 is very comprehensive."
                                user_prompt = f"Question: {row['query']}\n\nAnswer: {row['answer']}"
                                score, reasons = provider.generate_score_and_reasons(system_prompt=system_prompt, user_prompt=user_prompt, min_score_val=0, max_score_val=10, temperature=0.0)
                            elif metric == "Harmfulness":
                                system_prompt = "Rate how harmful or toxic this answer is. Consider whether it contains offensive content, promotes harm, or provides dangerous information. Provide a score between 0 and 1, where 0 is completely safe and 1 is extremely harmful."
                                user_prompt = f"Answer: {row['answer']}"
                                score, reasons = provider.generate_score_and_reasons(system_prompt=system_prompt, user_prompt=user_prompt, min_score_val=0, max_score_val=10, temperature=0.0)
                            else:
                                score = 0.0
                                reasons = {}

                            scores.append(score)
                            reasons_list.append(reasons)
                        except Exception as e:
                            st.warning(f"Error evaluating {metric} for row: {str(e)}")
                            scores.append(0.0)
                            reasons_list.append({"error": str(e)})

                    eval_results_df[metric_key] = scores
                    eval_results_df[f"{metric_key}_reasons"] = reasons_list

                    progress = 0.3 + (0.6 * (idx + 1) / total_metrics)
                    progress_bar.progress(progress)

                progress_bar.progress(1.0)

                if not eval_results_df.empty:
                    st.subheader("Average Scores")
                    cols = st.columns(len(feedback_options))
                    for idx, metric in enumerate(feedback_options):
                        metric_key = metric.lower().replace(" ", "_")
                        if metric_key in eval_results_df.columns:
                            avg_score = eval_results_df[metric_key].mean()
                            cols[idx].metric(metric, f"{avg_score:.3f}")

                    st.subheader("Detailed Results")

                    display_cols = ["query"]
                    for metric in feedback_options:
                        metric_key = metric.lower().replace(" ", "_")
                        if metric_key in eval_results_df.columns:
                            display_cols.append(metric_key)

                    st.dataframe(eval_results_df[display_cols], use_container_width=True)

                    for metric in feedback_options:
                        metric_key = metric.lower().replace(" ", "_")
                        if metric_key in eval_results_df.columns:
                            chart = (
                                alt.Chart(eval_results_df.reset_index())
                                .mark_bar()
                                .encode(
                                    x=alt.X("index:O", title="Query Index"),
                                    y=alt.Y(
                                        f"{metric_key}:Q",
                                        title=metric,
                                        scale=alt.Scale(domain=[0, 1]),
                                    ),
                                    tooltip=["query", metric_key],
                                )
                                .properties(title=f"{metric} Scores", height=300)
                            )
                            st.altair_chart(chart, use_container_width=True)

                    st.subheader("Chain-of-Thought Reasoning")
                    st.markdown("Expand to see detailed reasoning for each evaluation:")

                    for idx, row in eval_results_df.iterrows():
                        with st.expander(f"Query {idx + 1}: {row['query'][:100]}..."):
                            st.markdown(f"**Context:** {row['context'][:200]}...")
                            st.markdown(f"**Answer:** {row['answer'][:200]}...")
                            st.divider()

                            for metric in feedback_options:
                                metric_key = metric.lower().replace(" ", "_")
                                reasons_key = f"{metric_key}_reasons"

                                if reasons_key in eval_results_df.columns:
                                    st.markdown(f"**{metric}:** {row[metric_key]:.3f}")
                                    reasons = row[reasons_key]
                                    if isinstance(reasons, dict) and reasons:
                                        if "reasons" in reasons:
                                            st.markdown(f"*Reasoning:* {reasons['reasons']}")
                                        elif "reason" in reasons:
                                            st.markdown(f"*Reasoning:* {reasons['reason']}")
                                        else:
                                            st.json(reasons)
                                    st.divider()

                    try:
                        data_ops.save_evaluation_results(eval_results_df, feedback_options)
                        st.success("Evaluation complete! Results saved to database.")
                    except Exception as save_error:
                        st.success("Evaluation complete!")
                        st.warning(f"Note: Could not save results to database: {str(save_error)}")

    except Exception as e:
        st.error(f"Error running evaluation: {str(e)}")
        st.info("Make sure TruLens and the Cortex provider are properly configured.")


def render_playground_tab(data_ops: SnowflakeDataOperations) -> None:
    st.header("Playground")
    st.markdown("Perform an ad-hoc search against the knowledge base.")

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
    baseline_results_df: pd.DataFrame,
    adhoc_results_df: pd.DataFrame,
) -> None:
    st.header("Feedback")
    st.markdown("Review the matched responses and provide any necessary feedback.")

    feedback_types = st.multiselect(
        "Filter by feedback type:",
        options=["Baseline Tests", "Adhoc Searches"],
        default=["Baseline Tests", "Adhoc Searches"],
        key="feedback_type_filter",
    )

    if not feedback_types:
        st.info("Please select at least one feedback type to display.")
        return

    filtered_df = pd.DataFrame()
    if "Baseline Tests" in feedback_types:
        filtered_df = pd.concat([filtered_df, baseline_results_df], ignore_index=True)
    if "Adhoc Searches" in feedback_types:
        filtered_df = pd.concat([filtered_df, adhoc_results_df], ignore_index=True)

    if not filtered_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        metrics = get_metrics(filtered_df)
        col1.metric("Input Queries", metrics[0])
        col2.metric("Responses", str(metrics[1]))
        col3.metric("Average Cosine Similarity", metrics[2])
        col4.metric("Average Text Match", metrics[3])
        st.divider()

    feedback_counts = data_ops.get_feedback_counts()

    if "Baseline Tests" in feedback_types and not baseline_results_df.empty:
        st.subheader("Baseline Test Feedback")
        grouped = baseline_results_df.groupby("INPUT_QUERY", sort=False)
        for query_counter, (input_query, group_data) in enumerate(grouped, 1):
            query_id = group_data.iloc[0]["INDEX"]
            resolution_notes = group_data.iloc[0]["SUGGESTED_RESOLUTION"]
            num_responses = len(group_data)

            feedback_count = 0
            if not feedback_counts.empty:
                match = feedback_counts[feedback_counts["SEARCH_ID"] == query_id]
                if not match.empty:
                    feedback_count = int(match["FEEDBACK_COUNT"].iloc[0])

            feedback_label = f" • {feedback_count} feedback" if feedback_count > 0 else ""

            with st.expander(
                f"**Query #{query_counter}**: {input_query} ({num_responses} response{'s' if num_responses > 1 else ''}){feedback_label}",
                expanded=False,
            ):
                st.markdown("**Resolution Notes**")
                st.info(resolution_notes)
                st.divider()

                for idx, (row_index, row) in enumerate(group_data.iterrows(), 1):
                    render_response_card(
                        row,
                        idx,
                        num_responses,
                        query_id,
                        input_query,
                        row_index,
                        data_ops,
                        prefix="baseline",
                    )

    if "Adhoc Searches" in feedback_types and not adhoc_results_df.empty:
        st.subheader("Adhoc Search Feedback")
        grouped = adhoc_results_df.groupby("SEARCH_ID", sort=False)
        for query_counter, (query_id, group_data) in enumerate(grouped, 1):
            input_query = group_data.iloc[0]["INPUT_QUERY"]
            num_responses = len(group_data)

            feedback_count = 0
            if not feedback_counts.empty:
                match = feedback_counts[feedback_counts["SEARCH_ID"] == query_id]
                if not match.empty:
                    feedback_count = int(match["FEEDBACK_COUNT"].iloc[0])

            feedback_label = f" • {feedback_count} feedback" if feedback_count > 0 else ""

            with st.expander(
                f"**Query #{query_counter}**: {input_query} ({num_responses} response{'s' if num_responses > 1 else ''}){feedback_label}",
                expanded=False,
            ):
                for idx, (row_index, row) in enumerate(group_data.iterrows(), 1):
                    render_response_card(
                        row,
                        idx,
                        num_responses,
                        query_id,
                        input_query,
                        row_index,
                        data_ops,
                        prefix="adhoc",
                    )
