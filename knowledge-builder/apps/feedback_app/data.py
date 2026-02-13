"""Data loading and operations for the Feedback application."""

from datetime import datetime

import pandas as pd
import streamlit as st
from config import config
from snowflake.core import Root
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark import types as T
from snowflake.snowpark.context import get_active_session


def get_fqn(table: str) -> str:
    """Get fully qualified table name."""
    return f"{config.DATABASE}.{config.SCHEMA}.{table}"


def _get_search_ids_for_types(session: Session, input_types: tuple[str, ...]):
    """Get SEARCH_IDs filtered by input types. Returns a DataFrame for joining."""
    return session.table(get_fqn(config.SEARCH_QUERIES_TABLE)).filter(F.col("INPUT_TYPE").in_(list(input_types))).select("SEARCH_ID")


@st.cache_resource
def get_session() -> Session:
    """Get the active Snowpark session (cached)."""
    return get_active_session()


@st.cache_resource
def get_cortex_search_service(_session: Session):
    """Get the Cortex Search service."""
    root = Root(_session)
    return root.databases[config.DATABASE].schemas[config.SCHEMA].cortex_search_services[config.SEARCH_SERVICE]


@st.cache_data(ttl=300)
def get_input_types(_session: Session) -> list[str]:
    """Get distinct input types from search queries."""
    try:
        types_df = _session.table(get_fqn(config.SEARCH_QUERIES_TABLE)).select(F.col("INPUT_TYPE")).distinct().sort(F.col("INPUT_TYPE")).to_pandas()
        return types_df["INPUT_TYPE"].tolist()
    except Exception:
        return []


@st.cache_data(ttl=300)
def get_search_results(_session: Session, input_types: tuple[str, ...]) -> pd.DataFrame:
    """
    Extract search results for given input types.
    Args:
        input_types: Tuple of input types to filter by.
    Returns flattened results with SEARCH_ID, INPUT_QUERY, CHUNK_TEXT, KB_SYS_ID, scores.
    """
    try:
        chunk_text_expr = F.col("VALUE")["CHUNK_TEXT"].cast(T.StringType())
        kb_sys_id_expr = F.col("VALUE")["KB_SYS_ID"].cast(T.StringType())
        scores_expr = F.col("VALUE")["@scores"]
        cosine_similarity_expr = scores_expr["cosine_similarity"].cast(T.FloatType())
        text_match_expr = scores_expr["text_match"].cast(T.FloatType())
        reranker_score_expr = scores_expr["reranker_score"].cast(T.FloatType())

        results = (
            _session.table(get_fqn(config.SEARCH_QUERIES_TABLE))
            .filter(F.col("INPUT_TYPE").in_(list(input_types)))
            .with_column("INPUT_QUERY", F.col("INPUT_ARGS")["query"].cast(T.StringType()))
            .join_table_function("flatten", F.col("RESPONSE"))
            .select(
                "SEARCH_ID",
                "INPUT_QUERY",
                chunk_text_expr.alias("CHUNK_TEXT"),
                kb_sys_id_expr.alias("KB_SYS_ID"),
                cosine_similarity_expr.alias("COSINE_SIMILARITY"),
                text_match_expr.alias("TEXT_MATCH"),
                reranker_score_expr.alias("RERANKER_SCORE"),
                F.col("INPUT_TYPE"),
            )
        )
        return results.to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_feedback_counts(_session: Session) -> pd.DataFrame:
    """Get feedback counts per search ID."""
    try:
        return _session.table(get_fqn(config.SEARCH_FEEDBACK_TABLE)).group_by("SEARCH_ID").count().select(F.col("SEARCH_ID"), F.col("COUNT").alias("FEEDBACK_COUNT")).to_pandas()
    except Exception:
        return pd.DataFrame(columns=["SEARCH_ID", "FEEDBACK_COUNT"])


@st.cache_data(ttl=60)
def get_feedback_for_query(_session: Session, query_id: int) -> pd.DataFrame:
    """Get all feedback for a specific search query."""
    try:
        return _session.table(get_fqn(config.SEARCH_FEEDBACK_TABLE)).filter(F.col("SEARCH_ID") == F.lit(int(query_id))).select("USER_FEEDBACK", "USER_RATING", "CREATED_BY", "CREATED_ON").sort(F.col("CREATED_ON").desc()).to_pandas()
    except Exception:
        return pd.DataFrame(columns=["USER_FEEDBACK", "USER_RATING", "CREATED_BY", "CREATED_ON"])


@st.cache_data(ttl=300)
def get_average_scores(_session: Session, input_types: tuple[str, ...] | None = None) -> dict:
    """Get average scores across search results, optionally filtered by input types."""
    try:
        scores_expr = F.col("VALUE")["@scores"]
        cosine_expr = scores_expr["cosine_similarity"].cast(T.FloatType())
        text_match_expr = scores_expr["text_match"].cast(T.FloatType())
        reranker_expr = scores_expr["reranker_score"].cast(T.FloatType())

        base_query = _session.table(get_fqn(config.SEARCH_QUERIES_TABLE))
        if input_types:
            base_query = base_query.filter(F.col("INPUT_TYPE").in_(list(input_types)))

        scores_df = (
            base_query.join_table_function("flatten", F.col("RESPONSE"))
            .agg(
                F.avg(cosine_expr).alias("AVG_COSINE"),
                F.avg(text_match_expr).alias("AVG_TEXT_MATCH"),
                F.avg(reranker_expr).alias("AVG_RERANKER"),
            )
            .to_pandas()
        )

        eval_base = _session.table(get_fqn(config.EVALUATION_RESULTS_TABLE))
        if input_types:
            eval_base = eval_base.join(_get_search_ids_for_types(_session, input_types), on="SEARCH_ID", how="inner")

        eval_df = eval_base.agg(
            F.avg(F.col("EVALUATION")[0]["context_relevance"]["score"].cast(T.FloatType())).alias("AVG_CONTEXT_RELEVANCE"),
        ).to_pandas()

        def safe_float(df, col):
            """Safely extract float value, returning None for NaN."""
            if df.empty:
                return None
            val = df[col].iloc[0]
            return float(val) if val is not None and pd.notna(val) else None

        return {
            "cosine_similarity": safe_float(scores_df, "AVG_COSINE"),
            "text_match": safe_float(scores_df, "AVG_TEXT_MATCH"),
            "reranker_score": safe_float(scores_df, "AVG_RERANKER"),
            "context_relevance": safe_float(eval_df, "AVG_CONTEXT_RELEVANCE"),
        }
    except Exception:
        return {}


@st.cache_data(ttl=300)
def get_context_relevance_distribution(_session: Session, input_types: tuple[str, ...] | None = None) -> dict[str, int]:
    """
    Get distribution of context relevance scores bucketed by 0, 0.33, 0.66, 1.0.
    Returns dict with keys '0', '1', '2', '3' mapping to counts.
    """
    try:
        context_relevance_expr = F.col("EVALUATION")[0]["context_relevance"]["score"].cast(T.FloatType())

        eval_base = _session.table(get_fqn(config.EVALUATION_RESULTS_TABLE))
        if input_types:
            eval_base = eval_base.join(_get_search_ids_for_types(_session, input_types), on="SEARCH_ID", how="inner")

        # Bucket scores: 0 -> 0, 0.33 -> 1, 0.66 -> 2, 1.0 -> 3
        bucket_expr = F.when(context_relevance_expr <= 0.16, F.lit(0)).when(context_relevance_expr <= 0.5, F.lit(1)).when(context_relevance_expr <= 0.83, F.lit(2)).otherwise(F.lit(3))

        dist_df = eval_base.with_column("BUCKET", bucket_expr).group_by("BUCKET").count().to_pandas()

        result = {"0": 0, "1": 0, "2": 0, "3": 0}
        for _, row in dist_df.iterrows():
            bucket = str(int(row["BUCKET"]))
            result[bucket] = int(row["COUNT"])
        return result
    except Exception:
        return {"0": 0, "1": 0, "2": 0, "3": 0}


@st.cache_data(ttl=300)
def get_feedback_summary(_session: Session, input_types: tuple[str, ...] | None = None) -> dict:
    """
    Get aggregated feedback statistics.
    Returns dict with total_feedback, avg_rating, and rating_distribution.
    """
    try:
        feedback_base = _session.table(get_fqn(config.SEARCH_FEEDBACK_TABLE))

        if input_types:
            feedback_base = feedback_base.join(_get_search_ids_for_types(_session, input_types), on="SEARCH_ID", how="inner")

        # Get overall stats
        stats_df = feedback_base.agg(
            F.count("*").alias("TOTAL"),
            F.avg(F.col("USER_RATING")).alias("AVG_RATING"),
        ).to_pandas()

        # Get rating distribution
        dist_df = feedback_base.group_by("USER_RATING").count().to_pandas()

        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for _, row in dist_df.iterrows():
            rating = int(row["USER_RATING"])
            if 1 <= rating <= 5:
                rating_dist[rating] = int(row["COUNT"])

        total = int(stats_df["TOTAL"].iloc[0]) if not stats_df.empty else 0
        avg_val = stats_df["AVG_RATING"].iloc[0] if not stats_df.empty else None
        avg = float(avg_val) if avg_val is not None and pd.notna(avg_val) else None

        return {
            "total_feedback": total,
            "avg_rating": avg,
            "rating_distribution": rating_dist,
        }
    except Exception:
        return {"total_feedback": 0, "avg_rating": None, "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}


@st.cache_data(ttl=300)
def get_evaluation_results(_session: Session) -> pd.DataFrame:
    """
    Load evaluation results with extracted context relevance fields.
    Returns SEARCH_ID, INPUT_QUERY, CONTEXT_RELEVANCE_SCORE, CONTEXT_RELEVANCE_REASON.
    INPUT_QUERY is derived from SEARCH_QUERIES via SEARCH_ID join.
    """
    try:
        context_relevance_expr = F.col("EVALUATION")[0]["context_relevance"]
        context_relevance_reason_expr = context_relevance_expr["reasons"]["reason"].cast(T.StringType())
        context_relevance_score_expr = context_relevance_expr["score"].cast(T.FloatType())

        evaluation_results = _session.table(get_fqn(config.EVALUATION_RESULTS_TABLE)).select(
            "SEARCH_ID",
            "EVALUATION_MODEL",
            context_relevance_reason_expr.alias("CONTEXT_RELEVANCE_REASON"),
            context_relevance_score_expr.alias("CONTEXT_RELEVANCE_SCORE"),
        )

        search_queries = _session.table(get_fqn(config.SEARCH_QUERIES_TABLE)).select(
            "SEARCH_ID",
            F.col("INPUT_ARGS")["query"].cast(T.StringType()).alias("INPUT_QUERY"),
        )

        joined = evaluation_results.join(search_queries, on="SEARCH_ID", how="inner")
        return joined.to_pandas()
    except Exception:
        return pd.DataFrame(columns=["SEARCH_ID", "INPUT_QUERY", "EVALUATION_MODEL", "CONTEXT_RELEVANCE_REASON", "CONTEXT_RELEVANCE_SCORE"])


@st.cache_data(ttl=300)
def get_evaluation_status(_session: Session, input_types: tuple[str, ...] | None = None) -> dict:
    """Get evaluation status counts by input type, optionally filtered."""
    try:
        search_queries = _session.table(get_fqn(config.SEARCH_QUERIES_TABLE)).select("SEARCH_ID", "INPUT_TYPE")
        if input_types:
            search_queries = search_queries.filter(F.col("INPUT_TYPE").in_(list(input_types)))

        evaluated_ids = _session.table(get_fqn(config.EVALUATION_RESULTS_TABLE)).select("SEARCH_ID").distinct().with_column("_EVAL_MARKER", F.lit(1))

        queries_with_eval = search_queries.join(evaluated_ids, on="SEARCH_ID", how="left").with_column("IS_EVALUATED", F.when(F.col("_EVAL_MARKER").is_not_null(), F.lit(1)).otherwise(F.lit(0)))

        status_df = (
            queries_with_eval.group_by("INPUT_TYPE")
            .agg(
                F.sum("IS_EVALUATED").alias("EVALUATED_COUNT"),
                F.count("*").alias("TOTAL_COUNT"),
            )
            .to_pandas()
        )

        result = {}
        for _, row in status_df.iterrows():
            input_type = row["INPUT_TYPE"]
            result[input_type] = {
                "evaluated": int(row["EVALUATED_COUNT"]),
                "total": int(row["TOTAL_COUNT"]),
                "unevaluated": int(row["TOTAL_COUNT"]) - int(row["EVALUATED_COUNT"]),
            }
        return result
    except Exception:
        return {}


def run_search(session: Session, query: str, limit: int = None) -> tuple[dict, list]:
    """Execute a search and return results."""
    css = get_cortex_search_service(session)
    search_args = {
        "columns": ["CHUNK_TEXT", "KB_SYS_ID"],
        "filter": {},
        "limit": limit or config.SEARCH_LIMIT,
        "query": query,
    }
    response = css.search(**search_args)
    record = {
        "INPUT_QUERY": query,
        "RESPONSE": response.results,
        "INPUT_ARGS": search_args,
        "CREATED_ON": datetime.now(),
        "CREATED_BY": session.get_current_user(),
        "INPUT_TYPE": "ADHOC",
    }
    return record, response.results


def save_search(session: Session, record: dict) -> int | None:
    """Save a search record and return the new SEARCH_ID."""
    data = [
        [
            record["INPUT_TYPE"],
            record["INPUT_ARGS"],
            record["RESPONSE"],
            record["CREATED_BY"],
            record["CREATED_ON"],
        ]
    ]
    df = session.create_dataframe(
        data,
        schema=T.StructType(
            [
                T.StructField("INPUT_TYPE", T.StringType()),
                T.StructField("INPUT_ARGS", T.VariantType()),
                T.StructField("RESPONSE", T.VariantType()),
                T.StructField("CREATED_BY", T.StringType()),
                T.StructField("CREATED_ON", T.TimestampType()),
            ]
        ),
    )
    df.write.save_as_table(get_fqn(config.SEARCH_QUERIES_TABLE), mode="append", column_order="name")

    # Get the newly created SEARCH_ID
    saved = session.table(get_fqn(config.SEARCH_QUERIES_TABLE)).filter(F.col("INPUT_TYPE") == F.lit("ADHOC")).sort(F.col("CREATED_ON").desc()).limit(1).select("SEARCH_ID").collect()
    return saved[0]["SEARCH_ID"] if saved else None


def save_feedback(
    session: Session,
    search_id: int,
    rating: int,
    feedback: str,
    feedback_type: str = "CHUNK",
    chunk_index: int | None = None,
    anonymous: bool = False,
) -> None:
    """Save user feedback for a search result.

    Args:
        session: Snowpark session
        search_id: The search query ID
        rating: Star rating (1-5)
        feedback: User's text feedback
        feedback_type: 'CHUNK' for individual chunk feedback, 'AGENT_RESPONSE' for combined response
        chunk_index: 0-based index of the chunk (None for agent response)
        anonymous: Whether to submit anonymously
    """
    current_user = "Anonymous" if anonymous else (st.user.user_name if hasattr(st, "user") else session.get_current_user())
    data = [[int(search_id), feedback.strip(), rating, current_user, datetime.now(), feedback_type, chunk_index]]

    df = session.create_dataframe(
        data,
        schema=T.StructType(
            [
                T.StructField("SEARCH_ID", T.IntegerType()),
                T.StructField("USER_FEEDBACK", T.StringType()),
                T.StructField("USER_RATING", T.IntegerType()),
                T.StructField("CREATED_BY", T.StringType()),
                T.StructField("CREATED_ON", T.TimestampType()),
                T.StructField("FEEDBACK_TYPE", T.StringType()),
                T.StructField("CHUNK_INDEX", T.IntegerType()),
            ]
        ),
    )
    df.write.save_as_table(get_fqn(config.SEARCH_FEEDBACK_TABLE), mode="append", column_order="name")


def generate_combined_response(session: Session, chunks: list, query: str, model: str = "mistral-large2") -> str:
    """Generate a single LLM response using all chunks as context."""
    if not chunks:
        return ""

    combined_context = "\n\n---\n\n".join([chunk.get("CHUNK_TEXT", "") for chunk in chunks])

    result = (
        session.create_dataframe(
            [(combined_context, query)],
            schema=["context", "query"],
        )
        .with_column(
            "response",
            F.call_builtin(
                "SNOWFLAKE.CORTEX.COMPLETE",
                F.lit(model),
                F.concat(
                    F.lit("You are a helpful AI assistant. Use the following retrieved context to answer the user's question accurately and comprehensively.\n\n"),
                    F.lit("## Retrieved Context\n\n"),
                    F.col("context"),
                    F.lit("\n\n## User Question\n\n"),
                    F.col("query"),
                    F.lit("\n\n## Instructions\n\nProvide a clear, accurate answer based on the context above. If the context doesn't contain enough information to fully answer the question, say so."),
                ),
            ),
        )
        .select("response")
        .collect()
    )

    return result[0]["RESPONSE"] if result else ""


@st.cache_data(ttl=300)
def get_articles_for_chunks(_session: Session, chunk_texts: tuple[str, ...]) -> list[dict]:
    """
    Fetch articles for multiple chunks, grouped by article.
    Returns list of dicts: {number, short_description, text, chunk_indices: [0, 2, 4]}
    """
    if not chunk_texts:
        return []

    try:
        chunks_table = _session.table(get_fqn("KB_CHUNKS"))
        knowledge_table = _session.table(get_fqn("KB_KNOWLEDGE"))

        # Build a mapping of chunk_text -> chunk_index and lookup KB_SYS_ID for each
        article_to_chunks: dict[str, list[int]] = {}
        article_details: dict[str, dict] = {}

        for idx, chunk_text in enumerate(chunk_texts):
            if not chunk_text:
                continue

            # Look up KB_SYS_ID for this chunk
            chunk_result = chunks_table.filter(F.col("CHUNK_TEXT") == F.lit(chunk_text)).select("KB_SYS_ID").limit(1).collect()

            if not chunk_result:
                continue

            kb_sys_id = chunk_result[0]["KB_SYS_ID"]

            # Track which chunks map to this article
            if kb_sys_id not in article_to_chunks:
                article_to_chunks[kb_sys_id] = []
            article_to_chunks[kb_sys_id].append(idx)

            # Fetch article details if we haven't already
            if kb_sys_id not in article_details:
                article_result = knowledge_table.filter(F.col("NUMBER") == F.lit(kb_sys_id)).select("NUMBER", "SHORT_DESCRIPTION", "TEXT").limit(1).collect()
                if article_result:
                    row = article_result[0]
                    article_details[kb_sys_id] = {
                        "number": row["NUMBER"],
                        "short_description": row["SHORT_DESCRIPTION"],
                        "text": row["TEXT"],
                    }

        # Build result list
        results = []
        for kb_sys_id, chunk_indices in article_to_chunks.items():
            if kb_sys_id in article_details:
                article = article_details[kb_sys_id].copy()
                article["chunk_indices"] = chunk_indices
                results.append(article)

        # Sort by first chunk index to maintain relevance order
        results.sort(key=lambda x: x["chunk_indices"][0])
        return results

    except Exception:
        return []


def generate_feedback_agent_response(
    session: Session,
    chunks: pd.DataFrame,
    query: str,
    model: str = "mistral-large2",
) -> str:
    """
    Generate an agent response using chunk texts from a DataFrame.
    Used for the feedback tab to generate responses from search results.
    """
    if chunks.empty:
        return ""

    chunk_texts = chunks["CHUNK_TEXT"].tolist()
    combined_context = "\n\n---\n\n".join([str(t) for t in chunk_texts if t])

    result = (
        session.create_dataframe(
            [(combined_context, query)],
            schema=["context", "query"],
        )
        .with_column(
            "response",
            F.call_builtin(
                "SNOWFLAKE.CORTEX.COMPLETE",
                F.lit(model),
                F.concat(
                    F.lit("You are a helpful AI assistant. Use the following retrieved context to answer the user's question accurately and comprehensively.\n\n"),
                    F.lit("## Retrieved Context\n\n"),
                    F.col("context"),
                    F.lit("\n\n## User Question\n\n"),
                    F.col("query"),
                    F.lit("\n\n## Instructions\n\nProvide a clear, accurate answer based on the context above. If the context doesn't contain enough information to fully answer the question, say so."),
                ),
            ),
        )
        .select("response")
        .collect()
    )

    return result[0]["RESPONSE"] if result else ""
