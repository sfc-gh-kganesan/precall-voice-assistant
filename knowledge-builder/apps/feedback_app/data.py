"""
Data loading and operations for the Feedback application.
Uses Snowpark for data access with caching for performance.
"""

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
def get_search_results(_session: Session, input_type: str) -> pd.DataFrame:
    """
    Extract search results for a given input type.
    Returns flattened results with SEARCH_ID, INPUT_QUERY, CHUNK_TEXT, scores.
    """
    try:
        chunk_text_expr = F.col("VALUE")["CHUNK_TEXT"].cast(T.StringType())
        scores_expr = F.col("VALUE")["@scores"]
        cosine_similarity_expr = scores_expr["cosine_similarity"].cast(T.FloatType())
        text_match_expr = scores_expr["text_match"].cast(T.FloatType())

        results = (
            _session.table(get_fqn(config.SEARCH_QUERIES_TABLE))
            .filter(F.upper(F.col("INPUT_TYPE")) == F.lit(input_type.upper()))
            .with_column("INPUT_QUERY", F.col("INPUT_ARGS")["query"].cast(T.StringType()))
            .join_table_function("flatten", F.col("RESPONSE"))
            .select(
                "SEARCH_ID",
                "INPUT_QUERY",
                chunk_text_expr.alias("CHUNK_TEXT"),
                cosine_similarity_expr.alias("COSINE_SIMILARITY"),
                text_match_expr.alias("TEXT_MATCH"),
                F.lit(input_type).alias("INPUT_TYPE"),
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
def get_sync_status(_session: Session) -> dict:
    """Get counts of searched vs unsearched pairs."""
    try:
        results_table = _session.table(get_fqn(config.SEARCH_QUERIES_TABLE))
        total_golden = results_table.filter(F.upper(F.col("INPUT_TYPE")) == "GOLDEN_PAIR").count()
        total_synthetic = results_table.filter(F.upper(F.col("INPUT_TYPE")) == "SYNTHETIC_PAIR").count()
        total_adhoc = results_table.filter(F.upper(F.col("INPUT_TYPE")) == "ADHOC").count()

        return {
            "total_golden_pairs": total_golden,
            "total_synthetic_pairs": total_synthetic,
            "total_adhoc_queries": total_adhoc,
        }
    except Exception:
        return {"total_golden_pairs": 0, "total_synthetic_pairs": 0, "total_adhoc_queries": 0}


def run_search(session: Session, query: str, limit: int = None) -> tuple[dict, list]:
    """Execute a search and return results."""
    css = get_cortex_search_service(session)
    search_args = {
        "columns": ["CHUNK_TEXT"],
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


def save_feedback(session: Session, search_id: int, rating: int, feedback: str) -> None:
    """Save user feedback for a search result."""
    current_user = session.get_current_user()
    data = [[int(search_id), feedback.strip(), rating, current_user, datetime.now()]]

    df = session.create_dataframe(
        data,
        schema=T.StructType(
            [
                T.StructField("SEARCH_ID", T.IntegerType()),
                T.StructField("USER_FEEDBACK", T.StringType()),
                T.StructField("USER_RATING", T.IntegerType()),
                T.StructField("CREATED_BY", T.StringType()),
                T.StructField("CREATED_ON", T.TimestampType()),
            ]
        ),
    )
    df.write.save_as_table(get_fqn(config.SEARCH_FEEDBACK_TABLE), mode="append", column_order="name")


def generate_llm_response(session: Session, chunk_text: str, query: str, model: str = "mistral-large2") -> str:
    """Generate an LLM response for a single chunk."""
    result = (
        session.create_dataframe(
            [(chunk_text, query)],
            schema=["chunk_text", "query"],
        )
        .with_column(
            "response",
            F.call_builtin(
                "SNOWFLAKE.CORTEX.COMPLETE",
                F.lit(model),
                F.concat(
                    F.lit("You are a helpful AI assistant. Use the following context to answer the user's question.\n\nContext: "),
                    F.col("chunk_text"),
                    F.lit("\n\nUser Question: "),
                    F.col("query"),
                    F.lit("\n\nProvide a helpful and accurate answer based on the context provided."),
                ),
            ),
        )
        .select("response")
        .collect()
    )

    return result[0]["RESPONSE"] if result else ""


def generate_combined_response(session: Session, chunks: list, query: str, model: str = "mistral-large2") -> str:
    """Generate a single LLM response using all chunks as context."""
    if not chunks:
        return ""

    # Combine all chunk texts with separators
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
