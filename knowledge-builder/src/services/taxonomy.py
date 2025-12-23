import re
from typing import Iterable

import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.exceptions import SnowparkSQLException

VALID_SNOWFLAKE_IDENT = re.compile(r'^[A-Za-z0-9_.$"]+$')
VALID_SNOWFLAKE_COL = re.compile(r'^[A-Za-z0-9_$"]+$')

# Known source tables in TICKET_CANDIDATES
SOURCE_INCIDENT = "dmt_fct_incident"
SOURCE_RITM = "sc_req_item"  # placeholder - not yet in view


def validate_ident_or_error(value: str, label: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        st.error(f"{label} must be a non-empty string.")
        return False
    if not VALID_SNOWFLAKE_IDENT.match(value.strip()):
        st.error(
            f"{label} contains invalid characters. Use only letters, numbers, `_`, `.`, `$`, or quotes."
        )
        return False
    return True


def validate_col_or_error(value: str, label: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        st.error(f"{label} must be a non-empty string.")
        return False
    if not VALID_SNOWFLAKE_COL.match(value.strip()):
        st.error(
            f"{label} contains invalid characters. Use only letters, numbers, `_`, `$`, or quotes."
        )
        return False
    return True


@st.cache_data(show_spinner=False)
def snowflake_sql_df(sql: str) -> pd.DataFrame:
    """
    Execute SQL and return a Pandas dataframe.
    Uses the active Snowpark session so Streamlit caching never tries to hash a Session object.
    """
    session = get_active_session()
    return session.sql(sql).to_pandas()


def snowflake_relation_columns(relation_name: str) -> list[str]:
    """
    Return column names for a table/view.

    Prefer INFORMATION_SCHEMA (metadata) to avoid compiling views during DESCRIBE.
    Falls back to Snowpark schema introspection if needed.
    """
    session = get_active_session()
    # Try INFORMATION_SCHEMA first (works even when DESCRIBE/compilation of complex views fails).
    try:
        parts = [p.strip() for p in relation_name.split(".")]
        db = schema = obj = None
        if len(parts) == 3:
            db, schema, obj = parts
        elif len(parts) == 2:
            schema, obj = parts
            db = session.get_current_database()
        elif len(parts) == 1:
            obj = parts[0]
            db = session.get_current_database()
            schema = session.get_current_schema()

        if db and schema and obj and validate_ident_or_error(db, "Database"):
            sql = f"""
SELECT COLUMN_NAME
FROM {db}.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA ILIKE '{schema}'
  AND TABLE_NAME ILIKE '{obj}'
ORDER BY ORDINAL_POSITION;
"""
            cols_df = session.sql(sql).to_pandas()
            cols = cols_df["COLUMN_NAME"].tolist() if not cols_df.empty else []
            if cols:
                return cols
    except Exception:
        # Ignore and fall back to schema introspection
        pass

    # Fallback: Snowpark schema introspection (may compile views).
    return [f.name for f in session.table(relation_name).schema.fields]


def validate_cols_exist_or_error(relation_name: str, cols: Iterable[str]) -> bool:
    """
    Validate the provided column identifiers exist in the relation.
    Comparison is case-insensitive (Snowflake uppercases unquoted identifiers).
    """
    try:
        available = snowflake_relation_columns(relation_name)
    except SnowparkSQLException as e:
        st.error(
            f"Failed to read columns for `{relation_name}`. Is the view/table name correct?"
        )
        st.exception(e)
        return False

    available_set = {c.upper() for c in available}
    missing = [c for c in cols if c.upper() not in available_set]
    if missing:
        st.error(
            "One or more selected columns do not exist on the provided view/table.\n\n"
            f"Missing: {', '.join(missing)}"
        )
        with st.expander("Show available columns"):
            st.code(", ".join(sorted(available_set)))
        return False
    return True


@st.cache_data(show_spinner=False)
def get_available_attrs_keys(
    view_name: str, source_table: str, limit: int = 100
) -> list[str]:
    """
    Discover attribute keys available in the ATTRS JSON for a given source_table.
    Returns a list of key names found in the nested object.
    """
    sql = f"""
SELECT DISTINCT f.key::STRING AS attr_key
FROM {view_name},
     LATERAL FLATTEN(input => ATTRS['{source_table}']) f
WHERE source_table = '{source_table}'
LIMIT {limit};
"""
    try:
        df = snowflake_sql_df(sql)
        return sorted(df["ATTR_KEY"].tolist()) if not df.empty else []
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def ticket_taxonomy_summary(
    view_name: str,
    source_table: str,
    category_col: str,
    subcategory_col: str,
) -> pd.DataFrame:
    """
    Compute summary stats for category/subcategory fields from the ATTRS JSON.
    """
    sql = f"""
WITH base AS (
  SELECT
    ATTRS['{source_table}']:{category_col}::STRING AS category,
    ATTRS['{source_table}']:{subcategory_col}::STRING AS subcategory
  FROM {view_name}
  WHERE source_table = '{source_table}'
)
SELECT
  '{source_table}' AS source_table,
  COUNT(*) AS n_tickets,
  COUNT_IF(NULLIF(TRIM(category), '') IS NULL) AS empty_category,
  ROUND(100.0 * COUNT_IF(NULLIF(TRIM(category), '') IS NULL) / NULLIF(COUNT(*), 0), 2) AS pct_empty_category,
  COUNT_IF(NULLIF(TRIM(subcategory), '') IS NULL) AS empty_subcategory,
  ROUND(100.0 * COUNT_IF(NULLIF(TRIM(subcategory), '') IS NULL) / NULLIF(COUNT(*), 0), 2) AS pct_empty_subcategory,
  COUNT(DISTINCT NULLIF(TRIM(category), '')) AS unique_categories,
  COUNT(DISTINCT NULLIF(TRIM(subcategory), '')) AS unique_subcategories,
  COUNT(DISTINCT IFF(
    NULLIF(TRIM(category), '') IS NULL OR NULLIF(TRIM(subcategory), '') IS NULL,
    NULL,
    TRIM(category) || ' || ' || TRIM(subcategory)
  )) AS unique_category_subcategory_combos
FROM base;
"""
    return snowflake_sql_df(sql)


@st.cache_data(show_spinner=False)
def ticket_taxonomy_top_values(
    view_name: str,
    source_table: str,
    attr_col: str,
    limit: int = 50,
) -> pd.DataFrame:
    """
    Get top values for a single attribute column from ATTRS JSON.
    """
    sql = f"""
WITH base AS (
  SELECT ATTRS['{source_table}']:{attr_col}::STRING AS v
  FROM {view_name}
  WHERE source_table = '{source_table}'
)
SELECT
  TRIM(v) AS value,
  COUNT(*) AS count
FROM base
WHERE NULLIF(TRIM(v), '') IS NOT NULL
GROUP BY 1
ORDER BY count DESC
LIMIT {int(limit)};
"""
    return snowflake_sql_df(sql)


@st.cache_data(show_spinner=False)
def ticket_taxonomy_top_combos(
    view_name: str,
    source_table: str,
    category_col: str,
    subcategory_col: str,
    limit: int = 50,
) -> pd.DataFrame:
    """
    Get top (category, subcategory) combinations from ATTRS JSON.
    """
    sql = f"""
WITH base AS (
  SELECT
    ATTRS['{source_table}']:{category_col}::STRING AS category,
    ATTRS['{source_table}']:{subcategory_col}::STRING AS subcategory
  FROM {view_name}
  WHERE source_table = '{source_table}'
)
SELECT
  TRIM(category) AS category,
  TRIM(subcategory) AS subcategory,
  COUNT(*) AS count
FROM base
WHERE NULLIF(TRIM(category), '') IS NOT NULL
  AND NULLIF(TRIM(subcategory), '') IS NOT NULL
GROUP BY 1, 2
ORDER BY count DESC
LIMIT {int(limit)};
"""
    return snowflake_sql_df(sql)


@st.cache_data(show_spinner=False)
def ticket_taxonomy_missingness(
    view_name: str,
    source_table: str,
    category_col: str,
    subcategory_col: str,
) -> pd.DataFrame:
    """
    Compute missingness stats for category/subcategory fields.
    """
    sql = f"""
SELECT
  '{source_table}' AS source_table,
  COUNT(*) AS n,
  COUNT_IF(NULLIF(TRIM(ATTRS['{source_table}']:{category_col}::STRING), '') IS NULL) AS empty_category,
  COUNT_IF(NULLIF(TRIM(ATTRS['{source_table}']:{subcategory_col}::STRING), '') IS NULL) AS empty_subcategory
FROM {view_name}
WHERE source_table = '{source_table}';
"""
    return snowflake_sql_df(sql)


@st.cache_data(show_spinner=False)
def get_scoring_distribution(view_name: str, source_table: str) -> pd.DataFrame:
    """
    Show distribution of candidate_score from the SCORING column.
    """
    sql = f"""
SELECT
  SCORING:candidate_score::NUMBER AS candidate_score,
  COUNT(*) AS count
FROM {view_name}
WHERE source_table = '{source_table}'
GROUP BY 1
ORDER BY candidate_score DESC;
"""
    return snowflake_sql_df(sql)


@st.cache_data(show_spinner=False)
def get_assignment_group_distribution(
    view_name: str, source_table: str, limit: int = 25
) -> pd.DataFrame:
    """
    Show top assignment groups by frequency.
    """
    sql = f"""
SELECT
  ATTRS['{source_table}']:ASSIGNMENT_GROUP::STRING AS assignment_group,
  SCORING:assignment_group_freq_1y::NUMBER AS freq_1y,
  COUNT(*) AS count_in_sample
FROM {view_name}
WHERE source_table = '{source_table}'
GROUP BY 1, 2
ORDER BY count_in_sample DESC
LIMIT {limit};
"""
    return snowflake_sql_df(sql)


def render_ticket_taxonomy_tab() -> None:
    """
    Streamlit UI for the "ticket taxonomies" tab.
    Works with TICKET_CANDIDATES view (ATTRS as nested JSON).
    """
    st.subheader("Ticket Candidate Taxonomies")
    st.caption(
        "Analyze category/subcategory distributions from the TICKET_CANDIDATES view. "
        "This view stores ticket attributes as nested JSON in the ATTRS column, "
        "keyed by source_table (e.g., 'dmt_fct_incident')."
    )

    view_name = st.text_input(
        "Candidates view",
        value="DP_DSPR_DEV.DWH_LUMA.TICKET_CANDIDATES",
        help="Expected columns: SOURCE_TABLE, ATTRS (variant), SCORING (variant).",
    ).strip()

    if not validate_ident_or_error(view_name, "Candidates view"):
        return

    # Check what source tables are available
    try:
        source_tables_df = snowflake_sql_df(
            f"SELECT DISTINCT source_table FROM {view_name} ORDER BY 1"
        )
        available_sources = (
            source_tables_df["SOURCE_TABLE"].tolist()
            if not source_tables_df.empty
            else []
        )
    except SnowparkSQLException as e:
        st.error("Failed to query the view. Check the view name.")
        st.exception(e)
        return

    if not available_sources:
        st.warning("No source tables found in the view.")
        return

    st.info(f"Available source tables: {', '.join(available_sources)}")

    st.divider()

    # --- INCIDENT analysis ---
    if SOURCE_INCIDENT in available_sources:
        st.markdown("### Incident Analysis")

        col_left, col_right = st.columns(2)
        with col_left:
            incident_category_col = st.text_input(
                "Incident category attribute",
                value="CATEGORY",
                help="Attribute key within ATTRS[dmt_fct_incident]",
            ).strip()
        with col_right:
            incident_subcategory_col = st.text_input(
                "Incident subcategory attribute",
                value="U_ITS_SYMPTOM_BTS",
                help="Attribute key for subcategory (e.g., U_ITS_SYMPTOM_BTS from BTS symptom)",
            ).strip()

        # Show available keys button
        if st.button("Show available ATTRS keys for incidents", key="show_inc_keys"):
            with st.spinner("Fetching attribute keys..."):
                keys = get_available_attrs_keys(view_name, SOURCE_INCIDENT, limit=200)
                if keys:
                    st.code("\n".join(keys))
                else:
                    st.warning("Could not retrieve attribute keys.")

        if st.button(
            "Run Incident Taxonomy Analysis", type="primary", key="run_incident"
        ):
            if not validate_col_or_error(
                incident_category_col, "Incident category attribute"
            ):
                return
            if not validate_col_or_error(
                incident_subcategory_col, "Incident subcategory attribute"
            ):
                return

            try:
                st.markdown("#### Summary")
                summary = ticket_taxonomy_summary(
                    view_name,
                    SOURCE_INCIDENT,
                    incident_category_col,
                    incident_subcategory_col,
                )
                st.dataframe(summary, use_container_width=True)

                st.markdown("#### Missingness")
                miss = ticket_taxonomy_missingness(
                    view_name,
                    SOURCE_INCIDENT,
                    incident_category_col,
                    incident_subcategory_col,
                )
                st.dataframe(miss, use_container_width=True)

                st.markdown("#### Top Categories / Subcategories")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**{incident_category_col}**")
                    st.dataframe(
                        ticket_taxonomy_top_values(
                            view_name, SOURCE_INCIDENT, incident_category_col, limit=25
                        ),
                        use_container_width=True,
                    )
                with c2:
                    st.markdown(f"**{incident_subcategory_col}**")
                    st.dataframe(
                        ticket_taxonomy_top_values(
                            view_name,
                            SOURCE_INCIDENT,
                            incident_subcategory_col,
                            limit=25,
                        ),
                        use_container_width=True,
                    )

                st.markdown("#### Top (category, subcategory) Combos")
                st.dataframe(
                    ticket_taxonomy_top_combos(
                        view_name,
                        SOURCE_INCIDENT,
                        incident_category_col,
                        incident_subcategory_col,
                        limit=50,
                    ),
                    use_container_width=True,
                )

                st.markdown("#### Scoring Distribution")
                st.dataframe(
                    get_scoring_distribution(view_name, SOURCE_INCIDENT),
                    use_container_width=True,
                )

                st.markdown("#### Top Assignment Groups")
                st.dataframe(
                    get_assignment_group_distribution(
                        view_name, SOURCE_INCIDENT, limit=25
                    ),
                    use_container_width=True,
                )

            except SnowparkSQLException as e:
                st.error(
                    "Snowflake query failed. This may be due to an invalid attribute name. "
                    "Use 'Show available ATTRS keys' to see valid options."
                )
                st.exception(e)
                st.stop()

    else:
        st.info(f"Source table '{SOURCE_INCIDENT}' not found in view.")

    st.divider()

    # --- RITM analysis (placeholder) ---
    if SOURCE_RITM in available_sources:
        st.markdown("### Service Request (RITM) Analysis")

        col_left, col_right = st.columns(2)
        with col_left:
            ritm_category_col = st.text_input(
                "RITM category attribute",
                value="CATALOG_CATEGORY_PATH",
                help="Attribute key within ATTRS[sc_req_item]",
            ).strip()
        with col_right:
            ritm_subcategory_col = st.text_input(
                "RITM subcategory attribute",
                value="CATALOG_ITEM",
                help="Attribute key for subcategory",
            ).strip()

        if st.button("Show available ATTRS keys for RITMs", key="show_ritm_keys"):
            with st.spinner("Fetching attribute keys..."):
                keys = get_available_attrs_keys(view_name, SOURCE_RITM, limit=200)
                if keys:
                    st.code("\n".join(keys))
                else:
                    st.warning("Could not retrieve attribute keys.")

        if st.button("Run RITM Taxonomy Analysis", type="primary", key="run_ritm"):
            if not validate_col_or_error(ritm_category_col, "RITM category attribute"):
                return
            if not validate_col_or_error(
                ritm_subcategory_col, "RITM subcategory attribute"
            ):
                return

            try:
                st.markdown("#### Summary")
                summary = ticket_taxonomy_summary(
                    view_name,
                    SOURCE_RITM,
                    ritm_category_col,
                    ritm_subcategory_col,
                )
                st.dataframe(summary, use_container_width=True)

                st.markdown("#### Missingness")
                miss = ticket_taxonomy_missingness(
                    view_name,
                    SOURCE_RITM,
                    ritm_category_col,
                    ritm_subcategory_col,
                )
                st.dataframe(miss, use_container_width=True)

                st.markdown("#### Top Categories / Subcategories")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**{ritm_category_col}**")
                    st.dataframe(
                        ticket_taxonomy_top_values(
                            view_name, SOURCE_RITM, ritm_category_col, limit=25
                        ),
                        use_container_width=True,
                    )
                with c2:
                    st.markdown(f"**{ritm_subcategory_col}**")
                    st.dataframe(
                        ticket_taxonomy_top_values(
                            view_name, SOURCE_RITM, ritm_subcategory_col, limit=25
                        ),
                        use_container_width=True,
                    )

                st.markdown("#### Top (category, subcategory) Combos")
                st.dataframe(
                    ticket_taxonomy_top_combos(
                        view_name,
                        SOURCE_RITM,
                        ritm_category_col,
                        ritm_subcategory_col,
                        limit=50,
                    ),
                    use_container_width=True,
                )

            except SnowparkSQLException as e:
                st.error(
                    "Snowflake query failed. This may be due to an invalid attribute name. "
                    "Use 'Show available ATTRS keys' to see valid options."
                )
                st.exception(e)
                st.stop()
    else:
        st.info(
            f"Source table '{SOURCE_RITM}' not yet available in view. "
            "The RITM source is commented out in the TICKET_CANDIDATES definition."
        )
