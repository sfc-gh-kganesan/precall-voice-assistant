"""
Data loading and transformation functions for the Sunburst application.
Uses Snowpark for data access with caching for performance.
"""

import json

import pandas as pd
import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark import types as T
from snowflake.snowpark.context import get_active_session


@st.cache_resource
def get_session() -> Session:
    """Get the active Snowpark session (cached)."""
    return get_active_session()


@st.cache_data(ttl=300)
def get_synthetic_pairs(_session: Session) -> pd.DataFrame:
    """
    Load synthetic pairs from the SYNTHETIC_PAIRS table.
    Contains ticket data with LLM-generated taxonomy and features.
    """
    synthetic_pairs = _session.table("SYNTHETIC_PAIRS")
    return synthetic_pairs.to_pandas()


@st.cache_data(ttl=300)
def get_search_queries(_session: Session) -> pd.DataFrame:
    """
    Load search queries filtered to SYNTHETIC_PAIR input type.
    Contains the search execution records.
    Columns: SEARCH_ID, INPUT_TYPE, INPUT_ARGS, RESPONSE, CREATED_BY, CREATED_ON
    """
    input_type_expr = F.col("INPUT_TYPE") == "SYNTHETIC_PAIR"
    search_queries = _session.table("SEARCH_QUERIES").filter(input_type_expr).select("SEARCH_ID", "RESPONSE")
    return search_queries.to_pandas()


@st.cache_data(ttl=300)
def get_evaluation_results(_session: Session) -> pd.DataFrame:
    """
    Load evaluation results with extracted context relevance fields.
    This is where the context_relevance_score lives.
    """
    context_relevance_expr = F.col("EVALUATION")[0]["context_relevance"]
    context_relevance_reason_expr = context_relevance_expr["reasons"]["reason"].cast(T.StringType())
    context_relevance_score_expr = context_relevance_expr["score"].cast(T.FloatType())

    evaluation_results = _session.table("EVALUATION_RESULTS").select(
        "SEARCH_ID",
        "INPUT_QUERY",
        "CHUNKS",
        "EVALUATION_MODEL",
        context_relevance_reason_expr.alias("CONTEXT_RELEVANCE_REASON"),
        context_relevance_score_expr.alias("CONTEXT_RELEVANCE_SCORE"),
    )
    return evaluation_results.to_pandas()


def expand_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Expand a JSON/VARIANT column into normalized columns.
    Handles both string JSON and dict types.
    """
    if col not in df.columns:
        return df

    def parse_json(x):
        if pd.isna(x):
            return {}
        if isinstance(x, dict):
            return x
        try:
            return json.loads(x)
        except (json.JSONDecodeError, TypeError):
            return {}

    normalized_df = pd.json_normalize(df[col].apply(parse_json))
    normalized_df.index = df.index
    result = pd.concat([df.drop(col, axis=1), normalized_df], axis=1)
    return result


def expand_generated_col(df: pd.DataFrame) -> pd.DataFrame:
    """
    Specifically expand the GENERATED column which contains key fields:
    - query: the synthetic search query
    - answerable_with_kb: full/partial/no
    - taxonomy: l1-l4 classification
    - rationale: explanation
    """
    if "GENERATED" not in df.columns:
        return df

    def parse_generated(x):
        if pd.isna(x):
            return {}
        if isinstance(x, dict):
            return x
        try:
            return json.loads(x)
        except (json.JSONDecodeError, TypeError):
            return {}

    parsed = df["GENERATED"].apply(parse_generated)

    # Extract key fields
    df = df.copy()
    df["query"] = parsed.apply(lambda x: x.get("query", ""))
    df["answerable_with_kb"] = parsed.apply(lambda x: x.get("answerable_with_kb", ""))
    df["rationale"] = parsed.apply(lambda x: x.get("rationale", ""))
    df["expected_response"] = parsed.apply(lambda x: x.get("expected_response", ""))
    df["estimated_complexity"] = parsed.apply(lambda x: x.get("estimated_complexity", ""))
    df["recommendation"] = parsed.apply(lambda x: x.get("recommendation", ""))

    # Drop original GENERATED column
    df = df.drop("GENERATED", axis=1)

    return df


def expand_attrs_col(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand the ATTRS column to extract key ticket metadata fields.

    The ATTRS column contains nested JSON with ticket details:
    - SHORT_DESCRIPTION: ticket title
    - U_RESOLUTION_NOTES_BTS: resolution notes explaining what fixed the issue
    - U_RESOLUTION_BTS: resolution category
    - CATEGORY: issue category
    - U_ITS_SYMPTOM_BTS: symptom classification
    """
    if "ATTRS" not in df.columns:
        return df

    def parse_attrs(x):
        if pd.isna(x):
            return {}
        if isinstance(x, dict):
            # ATTRS is nested: {"dmt_fct_incident": {...}} or {"dmt_fct_request": {...}}
            # Get the first (and usually only) value
            for key in x:
                if isinstance(x[key], dict):
                    return x[key]
            return x
        try:
            parsed = json.loads(x)
            for key in parsed:
                if isinstance(parsed[key], dict):
                    return parsed[key]
            return parsed
        except (json.JSONDecodeError, TypeError):
            return {}

    parsed = df["ATTRS"].apply(parse_attrs)

    # Extract key metadata fields for knowledge gap analysis
    df = df.copy()
    df["SHORT_DESCRIPTION"] = parsed.apply(lambda x: x.get("SHORT_DESCRIPTION", ""))
    df["U_RESOLUTION_NOTES_BTS"] = parsed.apply(lambda x: x.get("U_RESOLUTION_NOTES_BTS", ""))
    df["U_RESOLUTION_BTS"] = parsed.apply(lambda x: x.get("U_RESOLUTION_BTS", ""))
    df["U_RESOLUTION_CODE_BTS"] = parsed.apply(lambda x: x.get("U_RESOLUTION_CODE_BTS", ""))
    df["CATEGORY"] = parsed.apply(lambda x: x.get("CATEGORY", ""))
    df["U_ITS_SYMPTOM_BTS"] = parsed.apply(lambda x: x.get("U_ITS_SYMPTOM_BTS", ""))

    # Drop original ATTRS column (it's large and no longer needed)
    df = df.drop("ATTRS", axis=1)

    return df


def extract_response_scores(df: pd.DataFrame) -> tuple[list[float], list[float]]:
    """
    Extract all cosine_similarity and text_match scores from the RESPONSE column.

    The RESPONSE column contains a list of search results, each with scoring metrics
    nested under the @scores key.

    Returns:
        Tuple of (all_cosine_scores, all_text_match_scores)
    """
    if "RESPONSE" not in df.columns:
        return [], []

    all_cosine_scores = []
    all_text_match_scores = []

    for response in df["RESPONSE"]:
        if pd.isna(response):
            continue

        data = response
        if isinstance(response, str):
            try:
                data = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                continue

        # RESPONSE is a list of results
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Scores are nested under @scores
                    scores = item.get("@scores", {})
                    if isinstance(scores, dict):
                        if "cosine_similarity" in scores and scores["cosine_similarity"] is not None:
                            all_cosine_scores.append(float(scores["cosine_similarity"]))
                        if "text_match" in scores and scores["text_match"] is not None:
                            all_text_match_scores.append(float(scores["text_match"]))

    return all_cosine_scores, all_text_match_scores


@st.cache_data(ttl=300)
def get_merged_data(_session: Session) -> pd.DataFrame:
    """
    Join all three tables to create the complete dataset for visualization.

    Join flow:
    SYNTHETIC_PAIRS.GENERATED['query'] = EVALUATION_RESULTS.INPUT_QUERY
    EVALUATION_RESULTS.SEARCH_ID = SEARCH_QUERIES.SEARCH_ID
    """
    # Load base dataframes
    synthetic_pairs_df = get_synthetic_pairs(_session)
    search_queries_df = get_search_queries(_session)
    evaluation_results_df = get_evaluation_results(_session)

    # Expand GENERATED column to get the query field
    expanded_df = expand_generated_col(synthetic_pairs_df)

    # Expand ATTRS column to get ticket metadata (resolution notes, etc.)
    expanded_df = expand_attrs_col(expanded_df)

    # First join: synthetic pairs to evaluation results on query
    merged = expanded_df.merge(evaluation_results_df, how="inner", left_on="query", right_on="INPUT_QUERY")

    # Second join: add search queries for response data
    merged = merged.merge(search_queries_df, how="inner", on="SEARCH_ID")

    # Clean up duplicate INPUT_QUERY columns
    if "INPUT_QUERY_x" in merged.columns:
        merged = merged.drop("INPUT_QUERY_x", axis=1)
    if "INPUT_QUERY_y" in merged.columns:
        merged = merged.rename(columns={"INPUT_QUERY_y": "INPUT_QUERY"})

    return merged


@st.cache_data(ttl=600)
def get_source_types(_session: Session) -> list[str]:
    """Get unique source types from synthetic pairs."""
    synthetic_pairs_df = get_synthetic_pairs(_session)
    return sorted(synthetic_pairs_df["SOURCE_TABLE"].dropna().unique().tolist())


@st.cache_data(ttl=600)
def get_answerable_options(_session: Session) -> list[str]:
    """Get unique answerable_with_kb values."""
    merged_df = get_merged_data(_session)
    return sorted(merged_df["answerable_with_kb"].dropna().unique().tolist())


def filter_data(
    df: pd.DataFrame,
    source_types: list[str],
    answerable_filter: list[str],
    selected_l1: str | None = None,
    selected_l2: str | None = None,
    selected_l3: str | None = None,
    selected_l4: str | None = None,
) -> pd.DataFrame:
    """
    Apply filters to the merged dataset.
    """
    filtered = df.copy()

    # Filter by source type
    if source_types:
        filtered = filtered[filtered["SOURCE_TABLE"].isin(source_types)]

    # Filter by answerable_with_kb
    if answerable_filter:
        filtered = filtered[filtered["answerable_with_kb"].isin(answerable_filter)]

    # Filter by sunburst selection (hierarchical)
    if selected_l1:
        filtered = filtered[filtered["L1_TAG"] == selected_l1]
    if selected_l2:
        filtered = filtered[filtered["L2_TAG"] == selected_l2]
    if selected_l3:
        filtered = filtered[filtered["L3_TAG"] == selected_l3]
    if selected_l4:
        filtered = filtered[filtered["L4_TAG"] == selected_l4]

    return filtered


def compute_kpis(df: pd.DataFrame, total_population: int | None = None) -> dict:
    """
    Compute KPI metrics from filtered dataframe.

    Args:
        df: Filtered dataframe to compute KPIs from
        total_population: Total number of records before filtering (for percentage calculation)
    """
    if df.empty:
        return {
            "ticket_count": 0,
            "total_population": total_population or 0,
            "ticket_pct_of_total": 0.0,
            "avg_context_relevance": None,
            "avg_cosine_similarity": None,
            "avg_text_match": None,
            "answerable_breakdown": {},
        }

    total = len(df)

    # Context relevance
    avg_context_relevance = df["CONTEXT_RELEVANCE_SCORE"].mean()

    # Cosine similarity and text match - flatten all results and aggregate
    cosine_scores, text_match_scores = extract_response_scores(df)
    avg_cosine_similarity = sum(cosine_scores) / len(cosine_scores) if cosine_scores else None
    avg_text_match = sum(text_match_scores) / len(text_match_scores) if text_match_scores else None

    # Answerable breakdown - compute percentages for all actual values
    answerable_counts = df["answerable_with_kb"].value_counts()
    answerable_breakdown = {value: (count / total * 100) for value, count in answerable_counts.items()}

    # Calculate percentage of total population
    total_pop = total_population or total
    ticket_pct = (total / total_pop * 100) if total_pop > 0 else 0.0

    return {
        "ticket_count": total,
        "total_population": total_pop,
        "ticket_pct_of_total": ticket_pct,
        "avg_context_relevance": avg_context_relevance,
        "avg_cosine_similarity": avg_cosine_similarity,
        "avg_text_match": avg_text_match,
        "answerable_breakdown": answerable_breakdown,
    }


def _extract_cosine_scores(response) -> list[float]:
    """Extract all cosine_similarity scores from a single RESPONSE value."""
    if pd.isna(response):
        return []
    data = response
    if isinstance(response, str):
        try:
            data = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return []
    scores = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                s = item.get("@scores", {})
                if isinstance(s, dict) and "cosine_similarity" in s and s["cosine_similarity"] is not None:
                    scores.append(float(s["cosine_similarity"]))
    return scores


def _extract_text_match_scores(response) -> list[float]:
    """Extract all text_match scores from a single RESPONSE value."""
    if pd.isna(response):
        return []
    data = response
    if isinstance(response, str):
        try:
            data = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return []
    scores = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                s = item.get("@scores", {})
                if isinstance(s, dict) and "text_match" in s and s["text_match"] is not None:
                    scores.append(float(s["text_match"]))
    return scores


def _flatten_and_mean(series: pd.Series) -> float | None:
    """Flatten a series of lists and compute the mean of all values."""
    all_values = []
    for lst in series:
        if isinstance(lst, list):
            all_values.extend(lst)
    return sum(all_values) / len(all_values) if all_values else None


def prepare_sunburst_data(
    df: pd.DataFrame,
    show_l1: bool = True,
    show_l2: bool = True,
    show_l3: bool = True,
    show_l4: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Prepare data for sunburst chart with dynamic path based on level visibility.
    Returns grouped dataframe and path columns list.
    """
    # Build path based on visible levels
    path_cols = []
    if show_l1:
        path_cols.append("L1_TAG")
    if show_l2:
        path_cols.append("L2_TAG")
    if show_l3:
        path_cols.append("L3_TAG")
    if show_l4:
        path_cols.append("L4_TAG")

    if not path_cols:
        path_cols = ["L1_TAG"]  # Default to L1 if nothing selected

    # Extract scores from RESPONSE into columns for aggregation
    df = df.copy()
    df["_cosine_scores"] = df["RESPONSE"].apply(_extract_cosine_scores)
    df["_text_match_scores"] = df["RESPONSE"].apply(_extract_text_match_scores)

    # Group by the visible levels and compute metrics
    grouped = (
        df.groupby(path_cols, dropna=False)
        .agg(
            {
                "CONTEXT_RELEVANCE_SCORE": "mean",
                "query": "count",
                "_cosine_scores": _flatten_and_mean,
                "_text_match_scores": _flatten_and_mean,
            }
        )
        .reset_index()
    )
    grouped = grouped.rename(
        columns={
            "query": "TICKET_COUNT",
            "_cosine_scores": "AVG_COSINE_SIMILARITY",
            "_text_match_scores": "AVG_TEXT_MATCH",
        }
    )

    # Fill NaN values for path columns
    for col in path_cols:
        grouped[col] = grouped[col].fillna("(empty)")

    return grouped, path_cols


def generate_knowledge_gap_summary(session: Session, filtered_df: pd.DataFrame) -> str:
    """
    Generate an AI summary of knowledge gaps using AI_AGG.

    Aggregates the context relevance chain-of-thought reasoning along with
    ticket metadata to identify patterns in missing knowledge.

    Args:
        session: Snowpark session
        filtered_df: The currently filtered dataframe with evaluation CoT traces

    Returns:
        AI-generated summary string
    """
    if filtered_df.empty:
        return "No data available for analysis."

    # Build evaluation texts with score, CoT reasoning, AND ticket context
    # Including ticket metadata helps explain WHY something wasn't answerable
    evaluations = []
    for _, row in filtered_df.iterrows():
        reason = row.get("CONTEXT_RELEVANCE_REASON")
        score = row.get("CONTEXT_RELEVANCE_SCORE")

        if pd.notna(reason):
            parts = []

            # Score
            score_str = f"{score:.2f}" if pd.notna(score) else "N/A"
            parts.append(f"Score: {score_str}")

            # Query and answerability from GENERATED
            query = row.get("query", "")
            if query:
                parts.append(f"Query: {query[:200]}")  # Truncate long queries

            answerable = row.get("answerable_with_kb", "")
            if answerable:
                parts.append(f"Answerable: {answerable}")

            rationale = row.get("rationale", "")
            if rationale:
                parts.append(f"Rationale: {rationale[:300]}")  # Truncate

            # Ticket metadata from ATTRS (if expanded)
            # Resolution notes are key - they explain what actually resolved the issue
            resolution_notes = row.get("U_RESOLUTION_NOTES_BTS", "")
            if pd.notna(resolution_notes) and resolution_notes:
                parts.append(f"Resolution: {str(resolution_notes)[:300]}")

            resolution = row.get("U_RESOLUTION_BTS", "")
            if pd.notna(resolution) and resolution:
                parts.append(f"Resolution Category: {resolution}")

            # CoT reasoning from evaluation
            parts.append(f"Evaluation: {reason[:500]}")  # Truncate very long CoT

            evaluations.append(" | ".join(parts))

    if not evaluations:
        return "No context relevance evaluations available."

    # Calculate avg score for context
    avg_score = filtered_df["CONTEXT_RELEVANCE_SCORE"].mean()
    avg_score_str = f"{avg_score:.2f}" if pd.notna(avg_score) else "N/A"

    # Create a temporary table with the evaluation texts
    eval_df = pd.DataFrame({"EVALUATION_TEXT": evaluations})
    snowpark_df = session.create_dataframe(eval_df)

    # AI_AGG instruction focused on explaining the score and identifying gaps
    instruction = (
        f"You are analyzing {len(evaluations)} context relevance evaluations from a knowledge base search system. "
        f"The average context relevance score is {avg_score_str} (0-1 scale, 1 = highly relevant). "
        "Each evaluation contains: the synthetic query, whether it was answerable by the KB, "
        "the rationale for answerability, actual ticket resolution notes, and the evaluation model's reasoning. "
        "Based on this data: "
        "1) Explain why the context relevance score is at its current level. "
        "2) Identify the most common knowledge gaps - what types of issues are NOT covered in the KB? "
        "3) Note any patterns in resolution notes that indicate missing documentation (e.g., many tickets resolved by 'aging' or requiring manual intervention). "
        "4) Provide 2-3 specific, actionable recommendations for KB improvements. "
        "Be concise (3-4 sentences). Focus on patterns, not individual cases."
    )

    result = snowpark_df.select(F.call_function("AI_AGG", F.col("EVALUATION_TEXT"), F.lit(instruction))).collect()

    if result and result[0][0]:
        return result[0][0]

    return "Unable to generate summary."
