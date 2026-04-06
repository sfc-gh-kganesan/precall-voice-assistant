from __future__ import annotations

import logging
from typing import Any

import yaml
from snowflake.snowpark import Session

from core.snowflake.exec import execute
from core.sql_utils import validate_identifier

logger = logging.getLogger(__name__)

TIME_DATA_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ", "TIMESTAMP_TZ"}
TIME_NAME_KEYWORDS = {"DATE", "DT", "TIMESTAMP", "TIME"}


def extract_yaml(session: Session, database: str, schema: str, sv_name: str) -> str:
    validate_identifier(database, "database")
    validate_identifier(schema, "schema")
    validate_identifier(sv_name, "semantic view name")
    fq_name = f'"{database}"."{schema}"."{sv_name}"'
    sql = f"SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{fq_name}') AS yaml_content"
    try:
        rows = execute(session, sql)
    except Exception as e:
        raise ValueError(f"SV '{sv_name}' not found in {database}.{schema}: {e}") from e
    if not rows:
        raise ValueError(f"No YAML returned for SV '{sv_name}' in {database}.{schema}")
    return rows[0]["YAML_CONTENT"]


def parse_yaml_metadata(yaml_content: str, sv_name: str, domain: str) -> dict[str, Any]:
    sv = yaml.safe_load(yaml_content)
    description = sv.get("description", "") or ""
    if description:
        sentences = [s.strip() for s in description.replace("\n", " ").split(".") if s.strip()]
        description = ". ".join(sentences[:5])
        if not description.endswith("."):
            description += "."
    table_names = [t.get("name", "") for t in sv.get("tables", []) if t.get("name")]
    lines = [f"Semantic View: {sv_name}", f"Domain: {domain}"]
    if description:
        lines.append(f"Description: {description}")
    if table_names:
        lines.append(f"Tables: {', '.join(table_names)}")
    return {"search_text": "\n".join(lines)}


def _ensure_sv_table(
    session: Session,
    database: str,
    schema: str,
    table_name: str = "SEMANTIC_VIEW_METADATA_SEARCH_SRC",
) -> None:
    validate_identifier(database, "database")
    validate_identifier(schema, "schema")
    validate_identifier(table_name, "table_name")
    sql = f"""
    CREATE TABLE IF NOT EXISTS "{database}"."{schema}"."{table_name}" (
        SEMANTIC_VIEW_NAME  VARCHAR(16777216) NOT NULL,
        DOMAIN              VARCHAR(16777216),
        SEARCH_TEXT         VARCHAR(16777216),
        SEMANTIC_VIEW_YAML  VARCHAR(16777216),
        UPDATED_AT          TIMESTAMP_LTZ    DEFAULT CURRENT_TIMESTAMP()
    )
    """
    execute(session, sql)


def _upsert_sv_row(
    session: Session,
    table_fqn: str,
    sv_name: str,
    domain: str,
    yaml_content: str,
    metadata: dict[str, Any],
) -> None:
    sql = f"""
    MERGE INTO {table_fqn} AS target
    USING (
        SELECT :1 AS SEMANTIC_VIEW_NAME, :2 AS DOMAIN, :3 AS SEARCH_TEXT, :4 AS SEMANTIC_VIEW_YAML
    ) AS source
    ON target.SEMANTIC_VIEW_NAME = source.SEMANTIC_VIEW_NAME
    WHEN MATCHED THEN UPDATE SET
        DOMAIN = source.DOMAIN, SEARCH_TEXT = source.SEARCH_TEXT,
        SEMANTIC_VIEW_YAML = source.SEMANTIC_VIEW_YAML, UPDATED_AT = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN INSERT (SEMANTIC_VIEW_NAME, DOMAIN, SEARCH_TEXT, SEMANTIC_VIEW_YAML, UPDATED_AT)
    VALUES (source.SEMANTIC_VIEW_NAME, source.DOMAIN, source.SEARCH_TEXT, source.SEMANTIC_VIEW_YAML, CURRENT_TIMESTAMP())
    """
    execute(session, sql, params=[sv_name, domain, metadata["search_text"], yaml_content])


def _create_sv_search_service(
    session: Session,
    database: str,
    schema: str,
    warehouse: str,
    service_name: str = "SEMANTIC_VIEW_METADATA_SEARCH",
    table_name: str = "SEMANTIC_VIEW_METADATA_SEARCH_SRC",
) -> None:
    validate_identifier(database, "database")
    validate_identifier(schema, "schema")
    validate_identifier(warehouse, "warehouse")
    validate_identifier(service_name, "service_name")
    validate_identifier(table_name, "table_name")
    sql = f"""
    CREATE OR REPLACE CORTEX SEARCH SERVICE "{database}"."{schema}"."{service_name}"
        ON SEARCH_TEXT
        ATTRIBUTES SEMANTIC_VIEW_NAME, DOMAIN
        WAREHOUSE = "{warehouse}"
        TARGET_LAG = '1 hour'
        AS (
            SELECT SEMANTIC_VIEW_NAME, DOMAIN, SEARCH_TEXT
            FROM "{database}"."{schema}"."{table_name}"
        )
    """
    execute(session, sql)


def sync_sv_registry(
    session: Session,
    sv_config: dict[str, str],
    database: str,
    schema: str,
    *,
    dry_run: bool = False,
    warehouse: str | None = None,
    table_name: str = "SEMANTIC_VIEW_METADATA_SEARCH_SRC",
    service_name: str = "SEMANTIC_VIEW_METADATA_SEARCH",
) -> dict[str, Any]:
    table_fqn = f'"{database}"."{schema}"."{table_name}"'
    _ensure_sv_table(session, database, schema, table_name)
    processed, skipped, errors = [], [], []
    for sv_name, domain in sv_config.items():
        try:
            yaml_content = extract_yaml(session, database, schema, sv_name)
            metadata = parse_yaml_metadata(yaml_content, sv_name, domain)
            if dry_run:
                skipped.append({"sv_name": sv_name, "reason": "dry_run"})
                continue
            _upsert_sv_row(session, table_fqn, sv_name, domain, yaml_content, metadata)
            processed.append(sv_name)
        except Exception as e:
            errors.append({"sv_name": sv_name, "error": str(e)})
            logger.error(f"Failed to sync SV '{sv_name}': {e}")
    search_service_created = False
    if warehouse and not dry_run and processed:
        try:
            _create_sv_search_service(
                session, database, schema, warehouse, service_name, table_name
            )
            search_service_created = True
        except Exception as e:
            errors.append({"sv_name": "_search_service_", "error": str(e)})
    return {
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "search_service_created": search_service_created,
    }
