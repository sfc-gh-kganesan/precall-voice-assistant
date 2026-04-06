from __future__ import annotations

import logging
from typing import Any

import yaml
from snowflake.snowpark import Session

from core.snowflake.exec import execute
from core.sql_utils import validate_identifier
from registry.sv_registry import TIME_DATA_TYPES, TIME_NAME_KEYWORDS, extract_yaml

logger = logging.getLogger(__name__)


def build_column_search_text(col_def: dict, col_type: str, table_name: str, sv_name: str) -> str:
    lines = [f"Column: {col_def.get('name', '')} ({col_type})"]
    if col_def.get("description"):
        lines.append(f"Description: {col_def['description']}")
    if col_def.get("synonyms"):
        syns = col_def["synonyms"]
        if isinstance(syns, list):
            lines.append(f"Synonyms: {', '.join(syns)}")
        else:
            lines.append(f"Synonyms: {syns}")
    if col_def.get("expr"):
        lines.append(f"Expression: {col_def['expr']}")
    if col_def.get("data_type"):
        lines.append(f"Data Type: {col_def['data_type']}")
    lines.append(f"Table: {table_name}")
    lines.append(f"Semantic View: {sv_name}")
    return "\n".join(lines)


def _is_time_dimension(dim: dict) -> bool:
    name = dim.get("name", "").upper()
    data_type = dim.get("data_type", "").upper()
    for dt in TIME_DATA_TYPES:
        if dt in data_type:
            return True
    for kw in TIME_NAME_KEYWORDS:
        if kw in name:
            return True
    return False


def parse_columns_from_yaml(yaml_content: str, sv_name: str, domain: str) -> list[dict[str, Any]]:
    sv = yaml.safe_load(yaml_content)
    columns: list[dict[str, Any]] = []
    for table in sv.get("tables", []):
        table_name = table.get("name", "")
        if not table_name:
            continue
        for dim in table.get("dimensions", []):
            if not dim.get("name"):
                continue
            col_type = "time_dimension" if _is_time_dimension(dim) else "dimension"
            columns.append(_build_col_row(dim, col_type, table_name, sv_name, domain))
        for td in table.get("time_dimensions", []):
            if not td.get("name"):
                continue
            columns.append(_build_col_row(td, "time_dimension", table_name, sv_name, domain))
        for fact in table.get("facts", []):
            if not fact.get("name"):
                continue
            columns.append(_build_col_row(fact, "fact", table_name, sv_name, domain))
        for metric in table.get("metrics", []):
            if not metric.get("name"):
                continue
            columns.append(_build_col_row(metric, "metric", table_name, sv_name, domain))
    for metric in sv.get("metrics", []):
        if not metric.get("name"):
            continue
        columns.append(_build_col_row(metric, "metric", sv_name, sv_name, domain))
    return columns


def _build_col_row(
    col_def: dict, col_type: str, table_name: str, sv_name: str, domain: str
) -> dict[str, Any]:
    return {
        "semantic_view_name": sv_name,
        "column_name": col_def.get("name", ""),
        "column_type": col_type,
        "domain": domain,
        "search_text": build_column_search_text(col_def, col_type, table_name, sv_name),
    }


def _ensure_column_table(
    session: Session, database: str, schema: str, table_name: str = "COLUMN_METADATA_SEARCH_SRC"
) -> None:
    validate_identifier(database, "database")
    validate_identifier(schema, "schema")
    validate_identifier(table_name, "table_name")
    sql = f"""
    CREATE TABLE IF NOT EXISTS "{database}"."{schema}"."{table_name}" (
        SEMANTIC_VIEW_NAME  VARCHAR(16777216) NOT NULL,
        COLUMN_NAME         VARCHAR(16777216) NOT NULL,
        COLUMN_TYPE         VARCHAR(16777216),
        DOMAIN              VARCHAR(16777216),
        SEARCH_TEXT         VARCHAR(16777216),
        UPDATED_AT          TIMESTAMP_LTZ    DEFAULT CURRENT_TIMESTAMP()
    )
    """
    execute(session, sql)


def _replace_sv_columns(
    session: Session, table_fqn: str, sv_name: str, columns: list[dict[str, Any]]
) -> None:
    execute(session, f"DELETE FROM {table_fqn} WHERE SEMANTIC_VIEW_NAME = :1", params=[sv_name])
    if not columns:
        return
    batch_size = 50
    for i in range(0, len(columns), batch_size):
        batch = columns[i : i + batch_size]
        placeholders = []
        params: list[Any] = []
        for j, col in enumerate(batch):
            base = j * 5
            placeholders.append(
                f"SELECT :{base + 1} AS SEMANTIC_VIEW_NAME, :{base + 2} AS COLUMN_NAME, :{base + 3} AS COLUMN_TYPE, :{base + 4} AS DOMAIN, :{base + 5} AS SEARCH_TEXT, CURRENT_TIMESTAMP() AS UPDATED_AT"
            )
            params.extend(
                [
                    col["semantic_view_name"],
                    col["column_name"],
                    col["column_type"],
                    col["domain"],
                    col["search_text"],
                ]
            )
        union_sql = " UNION ALL ".join(placeholders)
        insert_sql = f"INSERT INTO {table_fqn} (SEMANTIC_VIEW_NAME, COLUMN_NAME, COLUMN_TYPE, DOMAIN, SEARCH_TEXT, UPDATED_AT) {union_sql}"
        execute(session, insert_sql, params=params)


def _create_column_search_service(
    session: Session,
    database: str,
    schema: str,
    warehouse: str,
    service_name: str = "COLUMN_METADATA_SEARCH",
    table_name: str = "COLUMN_METADATA_SEARCH_SRC",
) -> None:
    validate_identifier(database, "database")
    validate_identifier(schema, "schema")
    validate_identifier(warehouse, "warehouse")
    validate_identifier(service_name, "service_name")
    validate_identifier(table_name, "table_name")
    sql = f"""
    CREATE OR REPLACE CORTEX SEARCH SERVICE "{database}"."{schema}"."{service_name}"
        ON SEARCH_TEXT
        ATTRIBUTES SEMANTIC_VIEW_NAME, COLUMN_NAME, COLUMN_TYPE, DOMAIN
        WAREHOUSE = "{warehouse}"
        TARGET_LAG = '1 hour'
        AS (
            SELECT SEMANTIC_VIEW_NAME, COLUMN_NAME, COLUMN_TYPE, DOMAIN, SEARCH_TEXT
            FROM "{database}"."{schema}"."{table_name}"
        )
    """
    execute(session, sql)


def sync_column_registry(
    session: Session,
    sv_config: dict[str, str],
    database: str,
    schema: str,
    *,
    dry_run: bool = False,
    warehouse: str | None = None,
    table_name: str = "COLUMN_METADATA_SEARCH_SRC",
    service_name: str = "COLUMN_METADATA_SEARCH",
) -> dict[str, Any]:
    table_fqn = f'"{database}"."{schema}"."{table_name}"'
    _ensure_column_table(session, database, schema, table_name)
    processed, skipped, errors = [], [], []
    total_columns = 0
    for sv_name, domain in sv_config.items():
        try:
            yaml_content = extract_yaml(session, database, schema, sv_name)
            columns = parse_columns_from_yaml(yaml_content, sv_name, domain)
            if dry_run:
                skipped.append({"sv_name": sv_name, "columns": len(columns), "reason": "dry_run"})
                continue
            _replace_sv_columns(session, table_fqn, sv_name, columns)
            processed.append(sv_name)
            total_columns += len(columns)
        except Exception as e:
            errors.append({"sv_name": sv_name, "error": str(e)})
            logger.error(f"Failed to sync columns for SV '{sv_name}': {e}")
    search_service_created = False
    if warehouse and not dry_run and processed:
        try:
            _create_column_search_service(
                session, database, schema, warehouse, service_name, table_name
            )
            search_service_created = True
        except Exception as e:
            errors.append({"sv_name": "_search_service_", "error": str(e)})
    return {
        "processed": processed,
        "total_columns": total_columns,
        "skipped": skipped,
        "errors": errors,
        "search_service_created": search_service_created,
    }
