from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from snowflake.snowpark import Session

from core.sql_utils import build_fqn

logger = logging.getLogger(__name__)


def connect(connection_name: str = "coco") -> Session:
    logger.info(f"Connecting to Snowflake (connection: {connection_name})")
    return Session.builder.config("connection_name", connection_name).getOrCreate()


def execute(session: Session, sql: str, params: list | None = None) -> list[dict[str, Any]]:
    if params:
        result_df = session.sql(sql, params=params)
    else:
        result_df = session.sql(sql)
    rows = result_df.collect()
    if rows:
        return [row.asDict() for row in rows]
    return []


@dataclass
class ColumnInfo:
    name: str
    type: str
    comment: str | None


def describe_table(session: Session, database: str, schema: str, table: str) -> list[ColumnInfo]:
    fqn = build_fqn(database, schema, table)
    sql = f"DESCRIBE TABLE {fqn}"
    rows = execute(session, sql)
    columns = []
    for row in rows:
        columns.append(
            ColumnInfo(
                name=row["name"],
                type=row["type"],
                comment=row.get("comment"),
            )
        )
    return columns
