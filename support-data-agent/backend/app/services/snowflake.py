from __future__ import annotations

from typing import Any

from snowflake.snowpark import Session

from ..config import snowflake_settings
from ..constants import DEFAULT_TABLE_PREVIEW_LIMIT
from ..exceptions import DataProcessingError, SnowflakeConnectionError
from ..logging_config import get_logger

logger = get_logger(__name__)

_session = None


def _get_session() -> Session:
    global _session
    if _session is None:
        try:
            connection_params = snowflake_settings.get_connection_params()
            # Log non-sensitive parameters
            debug_params = {k: v for k, v in connection_params.items() if k not in ["password", "private_key"]}
            logger.info("Attempting Snowflake connection", params=debug_params)

            _session = Session.builder.configs(connection_params).create()

            logger.info("Snowflake session created successfully")
        except Exception as e:
            logger.error("Failed to create Snowflake session", error=str(e))
            raise SnowflakeConnectionError(f"Failed to create Snowflake session: {str(e)}", e) from e
    return _session


def list_databases() -> list[str]:
    session = _get_session()
    try:
        rows = session.sql("select database_name from snowflake.account_usage.databases where deleted is null").collect()
        names = [r[0] for r in rows]
        if names:
            return sorted(names)
    except Exception as e:
        logger.warning(
            "Failed to query ACCOUNT_USAGE, falling back to SHOW DATABASES",
            error=str(e),
        )
        try:
            rows = session.sql("show databases").collect()
            return sorted([r[1] for r in rows])
        except Exception as fallback_error:
            logger.error("Failed to list databases", error=str(fallback_error))
            raise DataProcessingError(f"Failed to list databases: {str(fallback_error)}", "list_databases") from fallback_error
    return []


def list_schemas(database: str) -> list[str]:
    session = _get_session()
    try:
        rows = session.sql(f"select schema_name from {database}.information_schema.schemata").collect()
        return sorted([r[0] for r in rows])
    except Exception:
        rows = session.sql(f"show schemas in database {database}").collect()
        return sorted([r[1] for r in rows])


def list_tables(database: str, schema: str) -> list[dict[str, Any]]:
    session = _get_session()
    fully_qualified = f"{database}.{schema}"
    try:
        rows = session.sql(f"select table_name, row_count from {database}.information_schema.tables where table_schema = '{schema}' and table_type = 'BASE TABLE'").collect()
        return [{"name": r[0], "rowCount": int(r[1]) if r[1] is not None else 0} for r in rows]
    except Exception:
        rows = session.sql(f"show tables in schema {fully_qualified}").collect()
        results: list[dict[str, Any]] = []
        for r in rows:
            name = r[1]
            row_count = 0
            try:
                row_count = int(r[-1]) if isinstance(r[-1], (int, float)) else 0
            except Exception:
                row_count = 0
            results.append({"name": name, "rowCount": row_count})
        return results


def preview_table(database: str, schema: str, table: str, limit: int = None) -> dict[str, Any]:
    """
    Fetch a preview of table data including column names and sample rows.

    Args:
        database: Snowflake database name
        schema: Snowflake schema name
        table: Table name
        limit: Maximum number of rows to return

    Returns:
        Dictionary with 'columns' (list of column names) and 'rows' (list of row data)
    """
    session = _get_session()
    schema_qualified = f"{schema}.{table}"

    if limit is None:
        limit = DEFAULT_TABLE_PREVIEW_LIMIT

    describe_rows = session.sql(f"DESCRIBE TABLE {schema_qualified}").collect()
    columns = [row[0] for row in describe_rows]

    data_rows = session.sql(f"SELECT * FROM {schema_qualified} LIMIT {limit}").collect()
    rows = []
    for row in data_rows:
        row_dict = row.as_dict()
        rows.append(row_dict)

    return {"columns": columns, "rows": rows, "sampleCount": len(rows)}
