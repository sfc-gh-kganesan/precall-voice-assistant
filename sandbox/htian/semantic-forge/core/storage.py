from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from snowflake.snowpark import Session

from core.config import StorageConfig, get_config

logger = logging.getLogger(__name__)


def _ensure_table_exists(session: Session, storage_config: StorageConfig) -> None:
    table_name = storage_config.fully_qualified_table
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        DEPLOYMENT_ID VARCHAR(36) NOT NULL,
        DEPLOYED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        DEPLOYED_BY VARCHAR(256) DEFAULT CURRENT_USER(),
        SEMANTIC_ASSETS VARIANT NOT NULL,
        SEMANTIC_VIEW_NAMES ARRAY,
        MODEL_USED VARCHAR(64),
        VERSION_TAG VARCHAR(64),
        CONNECTION_NAME VARCHAR(64),
        PRIMARY KEY (DEPLOYMENT_ID)
    )
    """
    session.sql(create_sql).collect()


def _extract_view_names(semantic_assets: dict[str, Any]) -> list[str]:
    views = semantic_assets.get("semantic_assets", []) or semantic_assets.get("semantic_views", [])
    return [v.get("name", "unknown") for v in views]


def save_deployment(
    session: Session,
    semantic_assets: dict[str, Any],
    model_used: str = "openai-gpt-4.1",
    connection_name: str | None = None,
    version_tag: str | None = None,
    storage_config: StorageConfig | None = None,
) -> str:
    if storage_config is None:
        config = get_config()
        storage_config = config.storage
    _ensure_table_exists(session, storage_config)
    deployment_id = str(uuid.uuid4())
    view_names = _extract_view_names(semantic_assets)
    assets_json = json.dumps(semantic_assets)
    view_names_json = json.dumps(view_names)
    table_name = storage_config.fully_qualified_table
    insert_sql = f"""
    INSERT INTO {table_name} (
        DEPLOYMENT_ID, SEMANTIC_ASSETS, SEMANTIC_VIEW_NAMES, MODEL_USED, VERSION_TAG, CONNECTION_NAME
    )
    SELECT :1, PARSE_JSON(:2), PARSE_JSON(:3), :4, :5, :6
    """
    session.sql(
        insert_sql,
        params=[
            deployment_id,
            assets_json,
            view_names_json,
            model_used,
            version_tag or "",
            connection_name or "unknown",
        ],
    ).collect()
    return deployment_id


def get_deployment(
    session: Session, deployment_id: str, storage_config: StorageConfig | None = None
) -> dict[str, Any] | None:
    if storage_config is None:
        config = get_config()
        storage_config = config.storage
    table_name = storage_config.fully_qualified_table
    query = f"""
    SELECT DEPLOYMENT_ID, DEPLOYED_AT, DEPLOYED_BY, SEMANTIC_ASSETS, SEMANTIC_VIEW_NAMES, MODEL_USED, VERSION_TAG, CONNECTION_NAME
    FROM {table_name}
    WHERE DEPLOYMENT_ID = :1
    """
    result = session.sql(query, params=[deployment_id]).collect()
    if not result:
        return None
    row = result[0]
    return {
        "deployment_id": row["DEPLOYMENT_ID"],
        "deployed_at": row["DEPLOYED_AT"],
        "deployed_by": row["DEPLOYED_BY"],
        "semantic_assets": row["SEMANTIC_ASSETS"],
        "semantic_view_names": row["SEMANTIC_VIEW_NAMES"],
        "model_used": row["MODEL_USED"],
        "version_tag": row["VERSION_TAG"],
        "connection_name": row["CONNECTION_NAME"],
    }


def list_deployments(
    session: Session, limit: int = 10, storage_config: StorageConfig | None = None
) -> list[dict[str, Any]]:
    if storage_config is None:
        config = get_config()
        storage_config = config.storage
    table_name = storage_config.fully_qualified_table
    query = f"""
    SELECT DEPLOYMENT_ID, DEPLOYED_AT, DEPLOYED_BY, SEMANTIC_VIEW_NAMES, MODEL_USED, VERSION_TAG, CONNECTION_NAME
    FROM {table_name}
    ORDER BY DEPLOYED_AT DESC
    LIMIT :1
    """
    result = session.sql(query, params=[limit]).collect()
    return [
        {
            "deployment_id": row["DEPLOYMENT_ID"],
            "deployed_at": row["DEPLOYED_AT"],
            "deployed_by": row["DEPLOYED_BY"],
            "semantic_view_names": row["SEMANTIC_VIEW_NAMES"],
            "model_used": row["MODEL_USED"],
            "version_tag": row["VERSION_TAG"],
            "connection_name": row["CONNECTION_NAME"],
        }
        for row in result
    ]
