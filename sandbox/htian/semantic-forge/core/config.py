from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


@dataclass
class StorageConfig:
    database: str = "CLIENT_IQ"
    schema: str = "HTIAN"
    table: str = "SV_DEPLOYMENT_HISTORY"

    @property
    def fully_qualified_table(self) -> str:
        return f'"{self.database}"."{self.schema}"."{self.table}"'


@dataclass
class RegistryConfig:
    sv_table: str = "SEMANTIC_VIEW_METADATA_SEARCH_SRC"
    sv_service: str = "SEMANTIC_VIEW_METADATA_SEARCH"
    column_table: str = "COLUMN_METADATA_SEARCH_SRC"
    column_service: str = "COLUMN_METADATA_SEARCH"


@dataclass
class AgentConfig:
    name: str = "SEMANTIC_FORGE_AGENT"
    retrieval_tool: str = "RETRIEVAL_TOOL"
    sql_gen_tool: str = "SQL_GEN_TOOL"
    sql_exec_tool: str = "SQL_EXEC_TOOL"


@dataclass
class ForgeConfig:
    connection_name: str = "coco"
    source_database: str = "CLIENT_IQ"
    source_schema: str = "SANDBOX"
    target_database: str = "CLIENT_IQ"
    target_schema: str = "HTIAN"
    warehouse: str = "CLIENTIQ_WH_S"
    cortex_model: str = "openai-gpt-4.1"
    storage: StorageConfig = field(default_factory=StorageConfig)
    registry: RegistryConfig = field(default_factory=RegistryConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)


_config_cache: ForgeConfig | None = None


def load_config(config_path: str | Path | None = None) -> ForgeConfig:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        return ForgeConfig()

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    source = data.get("source", {})
    target = data.get("target", {})
    storage_data = data.get("storage", {})
    registry_data = data.get("registry", {})
    agent_data = data.get("agent", {})

    return ForgeConfig(
        connection_name=data.get("connection_name", "coco"),
        source_database=source.get("database", "CLIENT_IQ"),
        source_schema=source.get("schema", "SANDBOX"),
        target_database=target.get("database", "CLIENT_IQ"),
        target_schema=target.get("schema", "HTIAN"),
        warehouse=data.get("warehouse", "CLIENTIQ_WH_S"),
        cortex_model=data.get("cortex", {}).get("model", "openai-gpt-4.1"),
        storage=StorageConfig(
            database=storage_data.get("database", "CLIENT_IQ"),
            schema=storage_data.get("schema", "HTIAN"),
            table=storage_data.get("table", "SV_DEPLOYMENT_HISTORY"),
        ),
        registry=RegistryConfig(
            sv_table=registry_data.get("sv_table", "SEMANTIC_VIEW_METADATA_SEARCH_SRC"),
            sv_service=registry_data.get("sv_service", "SEMANTIC_VIEW_METADATA_SEARCH"),
            column_table=registry_data.get("column_table", "COLUMN_METADATA_SEARCH_SRC"),
            column_service=registry_data.get("column_service", "COLUMN_METADATA_SEARCH"),
        ),
        agent=AgentConfig(
            name=agent_data.get("name", "SEMANTIC_FORGE_AGENT"),
            retrieval_tool=agent_data.get("retrieval_tool", "RETRIEVAL_TOOL"),
            sql_gen_tool=agent_data.get("sql_gen_tool", "SQL_GEN_TOOL"),
            sql_exec_tool=agent_data.get("sql_exec_tool", "SQL_EXEC_TOOL"),
        ),
    )


def get_config(config_path: str | Path | None = None) -> ForgeConfig:
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config(config_path)
    return _config_cache


def clear_config_cache() -> None:
    global _config_cache
    _config_cache = None
