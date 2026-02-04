"""
Data loading and transformation functions for the Sunburst application.
Uses Snowpark for data access with caching for performance.
"""

import json
import re

import pandas as pd
import streamlit as st
from config import config
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
    synthetic_pairs = _session.table(config.SYNTHETIC_PAIRS_TABLE)
    return synthetic_pairs.to_pandas()


@st.cache_data(ttl=300)
def get_search_queries(_session: Session) -> pd.DataFrame:
    """
    Load search queries filtered to SYNTHETIC_PAIR input type.
    Contains the search execution records.
    Columns: SEARCH_ID, INPUT_TYPE, INPUT_ARGS, RESPONSE, CREATED_BY, CREATED_ON
    """
    input_type_expr = F.col("INPUT_TYPE") == "SYNTHETIC_PAIR"
    search_queries = _session.table(config.SEARCH_QUERIES_TABLE).filter(input_type_expr).select("SEARCH_ID", "RESPONSE")
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

    evaluation_results = _session.table(config.EVALUATION_RESULTS_TABLE).select(
        "SEARCH_ID",
        "INPUT_QUERY",
        "CHUNKS",
        "EVALUATION_MODEL",
        context_relevance_reason_expr.alias("CONTEXT_RELEVANCE_REASON"),
        context_relevance_score_expr.alias("CONTEXT_RELEVANCE_SCORE"),
    )
    return evaluation_results.to_pandas()


@st.cache_data(ttl=600)
def get_kb_chunks(_session: Session) -> pd.DataFrame:
    """
    Load KB_CHUNKS for KB_NUMBER lookup.
    """
    kb_chunks = _session.table(config.KB_CHUNKS_VIEW).select("KB_NUMBER", "CHUNK_TEXT")
    return kb_chunks.to_pandas()


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

    # Extract key fields for filtering and display
    df = df.copy()
    df["query"] = parsed.apply(lambda x: x.get("query", ""))
    df["answerable_with_kb"] = parsed.apply(lambda x: x.get("answerable_with_kb", ""))
    df["rationale"] = parsed.apply(lambda x: x.get("rationale", ""))
    df["expected_response"] = parsed.apply(lambda x: x.get("expected_response", ""))
    df["estimated_complexity"] = parsed.apply(lambda x: x.get("estimated_complexity", ""))
    df["recommendation"] = parsed.apply(lambda x: x.get("recommendation", ""))

    # Keep parsed dict for full JSON display in UI
    df["GENERATED_JSON"] = parsed

    # Drop original column
    df = df.drop("GENERATED", axis=1)

    return df


def expand_attrs_col(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand the ATTRS column to extract key ticket metadata fields.

    The ATTRS column contains nested JSON with ticket details:
    - SHORT_DESCRIPTION: ticket title
    - U_RESOLUTION_NOTES_BTS: resolution notes explaining what fixed the issue
    - U_RESOLUTION_BTS: resolution category (for incidents)
    - CATEGORY: issue category
    - U_ITS_SYMPTOM_BTS: symptom classification
    - STATE: request state (for sc_req_item)
    """
    if "ATTRS" not in df.columns:
        return df

    def parse_attrs(x):
        if pd.isna(x):
            return {}
        if isinstance(x, dict):
            # ATTRS is nested: {"dmt_fct_incident": {...}} or {"sc_req_item": {...}}
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
    # STATE field for service requests (sc_req_item)
    df["REQ_STATE"] = parsed.apply(lambda x: x.get("STATE", ""))

    # Keep parsed dict for full JSON display in UI
    df["ATTRS_JSON"] = parsed

    # Drop original column
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


def parse_response_articles(response_raw) -> list[dict]:
    """
    Parse and deduplicate articles from RESPONSE JSON.

    Pre-computes the article parsing that was previously done in the UI render loop.
    This allows caching at the data layer and avoids re-parsing on every row selection.

    Args:
        response_raw: Raw RESPONSE column value (JSON string or parsed list)

    Returns:
        List of article dicts with keys: summary, content, title, cosine_similarity,
        text_match, reranker_score
    """
    if pd.isna(response_raw) or not response_raw:
        return []

    # Parse RESPONSE as JSON if needed
    response_data = response_raw
    if isinstance(response_raw, str):
        try:
            response_data = json.loads(response_raw)
        except (json.JSONDecodeError, TypeError):
            return []

    if not isinstance(response_data, list) or len(response_data) == 0:
        return []

    articles = []
    seen_summaries = set()

    for item in response_data:
        if not isinstance(item, dict):
            continue

        # Extract scores
        scores = item.get("@scores", {})
        cosine_sim = scores.get("cosine_similarity") if isinstance(scores, dict) else None
        text_match = scores.get("text_match") if isinstance(scores, dict) else None
        reranker = scores.get("reranker_score") if isinstance(scores, dict) else None

        # Extract chunk text (contains DOC_SUMMARY and CHUNK_TEXT tags)
        chunk_text_raw = item.get("CHUNK_TEXT", "")

        # Parse DOC_SUMMARY and CHUNK_TEXT from the chunk
        summary_match = re.search(r"<DOC_SUMMARY>(.*?)</DOC_SUMMARY>", chunk_text_raw, re.DOTALL)
        content_match = re.search(r"<CHUNK_TEXT>(.*?)</CHUNK_TEXT>", chunk_text_raw, re.DOTALL)

        summary = summary_match.group(1).strip() if summary_match else ""
        content = content_match.group(1).strip() if content_match else chunk_text_raw

        # Extract title from summary (first line after # if markdown)
        title_match = re.search(r"^#\s*(.+?)$", summary, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None

        # Deduplicate by summary content (first 200 chars)
        dedup_key = summary[:200] if summary else content[:200]
        if dedup_key and dedup_key not in seen_summaries:
            seen_summaries.add(dedup_key)
            articles.append(
                {
                    "summary": summary,
                    "content": content,
                    "title": title,
                    "cosine_similarity": cosine_sim,
                    "text_match": text_match,
                    "reranker_score": reranker,
                }
            )

    return articles


def parse_response_chunks(response_raw, chunk_to_kb: dict) -> list[dict]:
    """
    Parse chunks from RESPONSE JSON with KB_NUMBER mapping.

    Unlike parse_response_articles which deduplicates, this returns all chunks
    for accurate frequency counts in the leaderboard.

    Args:
        response_raw: Raw RESPONSE column value (JSON string or parsed list)
        chunk_to_kb: Dict mapping CHUNK_TEXT to KB_NUMBER

    Returns:
        List of chunk dicts with keys: CHUNK_TEXT, KB_NUMBER, COSINE_SIMILARITY,
        RERANKER_SCORE, TEXT_MATCH
    """
    if pd.isna(response_raw) or not response_raw:
        return []

    # Parse RESPONSE as JSON if needed
    response_data = response_raw
    if isinstance(response_raw, str):
        try:
            response_data = json.loads(response_raw)
        except (json.JSONDecodeError, TypeError):
            return []

    if not isinstance(response_data, list) or len(response_data) == 0:
        return []

    chunks = []
    for item in response_data:
        if not isinstance(item, dict):
            continue

        chunk_text = item.get("CHUNK_TEXT", "")
        if not chunk_text:
            continue

        scores = item.get("@scores", {})
        if not isinstance(scores, dict):
            scores = {}

        chunks.append(
            {
                "CHUNK_TEXT": chunk_text,
                "KB_NUMBER": chunk_to_kb.get(chunk_text),
                "COSINE_SIMILARITY": scores.get("cosine_similarity"),
                "RERANKER_SCORE": scores.get("reranker_score"),
                "TEXT_MATCH": scores.get("text_match"),
            }
        )

    return chunks


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

    # Load KB_CHUNKS for chunk-to-article mapping (used for leaderboard)
    kb_chunks_df = get_kb_chunks(_session)
    chunk_to_kb = dict(zip(kb_chunks_df["CHUNK_TEXT"], kb_chunks_df["KB_NUMBER"], strict=False))

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

    # Precompute expensive boolean masks (avoids re-computing on every filter)
    merged["IS_UNRESOLVED"] = merged.apply(_is_unresolved, axis=1)
    merged["IS_BACKFILLABLE"] = merged.apply(_is_backfillable, axis=1)

    # Precompute parsed articles from RESPONSE (avoids re-parsing on every row selection)
    merged["PARSED_ARTICLES"] = merged["RESPONSE"].apply(parse_response_articles)

    # Precompute parsed chunks with KB_NUMBER for leaderboard (not deduplicated)
    merged["PARSED_CHUNKS"] = merged["RESPONSE"].apply(lambda r: parse_response_chunks(r, chunk_to_kb))

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


def get_resolution_options() -> list[str]:
    """Get resolution status options (Resolved/Unresolved)."""
    return ["Resolved", "Unresolved"]


def get_backfillable_options() -> list[str]:
    """Get backfillable status options (Yes / No)."""
    return ["Yes", "No"]


def filter_data(
    df: pd.DataFrame,
    source_types: list[str],
    answerable_filter: list[str],
    resolution_filter: list[str] | None = None,
    backfillable_filter: list[str] | None = None,
    selected_l1: str | None = None,
    selected_l2: str | None = None,
    selected_l3: str | None = None,
    selected_l4: str | None = None,
    all_source_types: list[str] | None = None,
    all_answerable_options: list[str] | None = None,
) -> pd.DataFrame:
    """
    Apply filters to the merged dataset.

    When a filter list matches all available options (or is empty), no filtering is applied.
    This ensures consistent behavior between "all selected" and "none selected".
    """
    filtered = df.copy()

    # Filter by source type (only if proper subset selected)
    if source_types and (all_source_types is None or set(source_types) != set(all_source_types)):
        filtered = filtered[filtered["SOURCE_TABLE"].isin(source_types)]

    # Filter by answerable_with_kb (only if proper subset selected)
    if answerable_filter and (all_answerable_options is None or set(answerable_filter) != set(all_answerable_options)):
        filtered = filtered[filtered["answerable_with_kb"].isin(answerable_filter)]

    # Filter by resolution status (Resolved/Unresolved)
    # Only apply filter if exactly one option selected (not both, not none)
    # Uses precomputed IS_UNRESOLVED column for performance
    if resolution_filter and len(resolution_filter) == 1:
        if "Unresolved" in resolution_filter:
            filtered = filtered[filtered["IS_UNRESOLVED"]]
        elif "Resolved" in resolution_filter:
            filtered = filtered[~filtered["IS_UNRESOLVED"]]

    # Filter by backfillable status (Yes / No)
    # Only apply filter if exactly one option selected (not both, not none)
    # Uses precomputed IS_BACKFILLABLE column for performance
    if backfillable_filter and len(backfillable_filter) == 1:
        if "Yes" in backfillable_filter:
            filtered = filtered[filtered["IS_BACKFILLABLE"]]
        elif "No" in backfillable_filter:
            filtered = filtered[~filtered["IS_BACKFILLABLE"]]

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


def _is_unresolved(row: pd.Series) -> bool:
    """
    Determine if a ticket was unresolved/cancelled based on source type.

    For incidents (dmt_fct_incident): U_RESOLUTION_BTS starts with "Cancelled"
    For service requests (sc_req_item): REQ_STATE == "Closed Incomplete"
    """
    source = row.get("SOURCE_TABLE", "")
    if source == "dmt_fct_incident":
        resolution = row.get("U_RESOLUTION_BTS", "")
        if pd.notna(resolution) and resolution:
            return str(resolution).startswith("Cancelled")
    elif source == "sc_req_item":
        state = row.get("REQ_STATE", "")
        if pd.notna(state) and state:
            return state == "Closed Incomplete"
    return False


def _is_backfillable(row: pd.Series) -> bool:
    """
    Determine if a ticket has substantive resolution notes that could be used to backfill knowledge.

    For incidents (dmt_fct_incident): U_RESOLUTION_NOTES_BTS is non-empty and non-trivial
    For service requests (sc_req_item): Currently no equivalent field, returns False

    Excludes trivial notes like aging/stale closures, very short notes, or boilerplate.
    """
    source = row.get("SOURCE_TABLE", "")
    if source == "dmt_fct_incident":
        notes = row.get("U_RESOLUTION_NOTES_BTS", "")
        if pd.notna(notes) and notes:
            notes_str = str(notes).strip()
            # Exclude trivial/boilerplate notes
            if len(notes_str) < 50:
                return False
            notes_lower = notes_str.lower()
            trivial_patterns = [
                "due to aging",
                "lack of updates",
                "no response from user",
                "no response from customer",
                "closed due to inactivity",
                "auto-closed",
                "autoclosed",
                "duplicate incident",
                "duplicate ticket",
                "transferred to",
                "reassigned to",
            ]
            for pattern in trivial_patterns:
                if pattern in notes_lower:
                    return False
            return True
    # sc_req_item doesn't have resolution notes field
    return False


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
            "unresolved_count": 0,
            "unresolved_pct": 0.0,
            "coverage_count": 0,
            "coverage_pct": 0.0,
            "backfillable_count": 0,
            "backfillable_pct": 0.0,
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

    # Unresolved/Cancelled tickets (uses precomputed column)
    unresolved_count = df["IS_UNRESOLVED"].sum()
    unresolved_pct = (unresolved_count / total * 100) if total > 0 else 0.0

    # Coverage: tickets with context_relevance >= 0.8
    coverage_mask = df["CONTEXT_RELEVANCE_SCORE"] >= 0.8
    coverage_count = coverage_mask.sum()
    coverage_pct = (coverage_count / total * 100) if total > 0 else 0.0

    # Backfillable: tickets with resolution notes (uses precomputed column)
    backfillable_count = df["IS_BACKFILLABLE"].sum()
    backfillable_pct = (backfillable_count / total * 100) if total > 0 else 0.0

    return {
        "ticket_count": total,
        "total_population": total_pop,
        "ticket_pct_of_total": ticket_pct,
        "avg_context_relevance": avg_context_relevance,
        "avg_cosine_similarity": avg_cosine_similarity,
        "avg_text_match": avg_text_match,
        "answerable_breakdown": answerable_breakdown,
        "unresolved_count": unresolved_count,
        "unresolved_pct": unresolved_pct,
        "coverage_count": coverage_count,
        "coverage_pct": coverage_pct,
        "backfillable_count": backfillable_count,
        "backfillable_pct": backfillable_pct,
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


def compute_kb_leaderboard(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute KB article leaderboard from precomputed PARSED_CHUNKS column.

    Aggregates retrieval frequency and average scores per KB article.

    Args:
        merged_df: The merged dataframe with PARSED_CHUNKS and CONTEXT_RELEVANCE_SCORE

    Returns:
        DataFrame with columns: KB_NUMBER, FREQUENCY, AVG_COSINE_SIMILARITY,
        AVG_RERANKER_SCORE, AVG_TEXT_MATCH, AVG_CONTEXT_RELEVANCE
    """
    empty_result = pd.DataFrame(columns=["KB_NUMBER", "FREQUENCY", "AVG_COSINE_SIMILARITY", "AVG_RERANKER_SCORE", "AVG_TEXT_MATCH", "AVG_CONTEXT_RELEVANCE"])

    if merged_df.empty or "PARSED_CHUNKS" not in merged_df.columns:
        return empty_result

    # Flatten PARSED_CHUNKS and add context relevance from each row
    rows = []
    for _, row in merged_df.iterrows():
        chunks = row.get("PARSED_CHUNKS", [])
        context_relevance = row.get("CONTEXT_RELEVANCE_SCORE")

        if not chunks:
            continue

        for chunk in chunks:
            if chunk.get("KB_NUMBER"):  # Only include chunks with KB mapping
                rows.append(
                    {
                        "KB_NUMBER": chunk["KB_NUMBER"],
                        "COSINE_SIMILARITY": chunk.get("COSINE_SIMILARITY"),
                        "RERANKER_SCORE": chunk.get("RERANKER_SCORE"),
                        "TEXT_MATCH": chunk.get("TEXT_MATCH"),
                        "CONTEXT_RELEVANCE": context_relevance,
                    }
                )

    if not rows:
        return empty_result

    flattened_df = pd.DataFrame(rows)

    # Aggregate by KB_NUMBER
    leaderboard = (
        flattened_df.groupby("KB_NUMBER")
        .agg(
            FREQUENCY=("KB_NUMBER", "count"),
            AVG_COSINE_SIMILARITY=("COSINE_SIMILARITY", "mean"),
            AVG_RERANKER_SCORE=("RERANKER_SCORE", "mean"),
            AVG_TEXT_MATCH=("TEXT_MATCH", "mean"),
            AVG_CONTEXT_RELEVANCE=("CONTEXT_RELEVANCE", "mean"),
        )
        .reset_index()
    )

    # Sort by frequency descending
    leaderboard = leaderboard.sort_values("FREQUENCY", ascending=False)

    return leaderboard


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
