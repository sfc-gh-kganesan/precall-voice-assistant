from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


class GenerateSQLError(Exception):
    pass


def load_semantic_assets(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise GenerateSQLError(f"Semantic assets file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_dimension(column: dict[str, Any]) -> dict[str, Any]:
    dim: dict[str, Any] = {"name": column["name"], "expr": column["name"]}
    if column.get("description"):
        dim["description"] = column["description"]
    if column.get("synonyms"):
        dim["synonyms"] = column["synonyms"]
    if column.get("glossary"):
        dim["comment"] = column["glossary"]
    return dim


def generate_table_yaml(
    table: dict[str, Any],
    source_database: str,
    source_schema: str,
    primary_key: str | None = None,
    unique_keys: list[str] | None = None,
) -> dict[str, Any]:
    result = {
        "name": table["name"],
        "base_table": {
            "database": source_database,
            "schema": source_schema,
            "table": table["name"],
        },
    }
    if primary_key:
        result["primary_key"] = {"columns": [primary_key]}
    if unique_keys:
        result["unique_keys"] = [{"columns": [key]} for key in unique_keys]
    result["dimensions"] = [generate_dimension(col) for col in table.get("columns", [])]
    return result


def generate_semantic_view_yaml(
    asset: dict[str, Any], source_database: str, source_schema: str
) -> str:
    tables = asset.get("tables", [])
    relationships = asset.get("relationships", [])
    table_unique_keys: dict[str, set[str]] = {}
    for rel in relationships:
        parent_table = rel.get("left_table", "")
        for cond in rel.get("on", []):
            parent_col = cond.get("left_column", "")
            if parent_table and parent_col:
                if parent_table not in table_unique_keys:
                    table_unique_keys[parent_table] = set()
                table_unique_keys[parent_table].add(parent_col)
    table_yamls = []
    for table in tables:
        table_name = table["name"]
        primary_key = None
        for col in table.get("columns", []):
            col_name = col.get("name", "")
            if col_name.endswith("_KEY"):
                primary_key = col_name
                break
        unique_keys = list(table_unique_keys.get(table_name, set()))
        if primary_key and primary_key in unique_keys:
            unique_keys.remove(primary_key)
        table_yaml = generate_table_yaml(
            table,
            source_database,
            source_schema,
            primary_key=primary_key,
            unique_keys=unique_keys if unique_keys else None,
        )
        table_yamls.append(table_yaml)
    sv_yaml = {
        "name": asset["name"],
        "description": asset.get("description", ""),
        "tables": table_yamls,
    }
    if relationships:
        sv_relationships = []
        for i, rel in enumerate(relationships):
            parent_table = rel.get("left_table", "")
            child_table = rel.get("right_table", "")
            sv_rel = {
                "name": f"{asset['name']}_rel_{i}",
                "left_table": child_table,
                "right_table": parent_table,
                "relationship_columns": [
                    {"left_column": cond["right_column"], "right_column": cond["left_column"]}
                    for cond in rel.get("on", [])
                ],
            }
            sv_relationships.append(sv_rel)
        sv_yaml["relationships"] = sv_relationships
    return yaml.dump(sv_yaml, default_flow_style=False, sort_keys=False, allow_unicode=True)


def generate_sql_statement(
    asset: dict[str, Any],
    source_database: str,
    source_schema: str,
    target_database: str,
    target_schema: str,
) -> str:
    inner_yaml = generate_semantic_view_yaml(asset, source_database, source_schema)
    table_names = ", ".join(t["name"] for t in asset.get("tables", []))
    domains = ", ".join(asset.get("domains", []))
    header = f"""    -- ==================================================
    -- Semantic View: {asset["name"]}
    -- Domains: {domains}
    -- Tables: {table_names}
    -- =================================================="""
    target_location = f"{target_database}.{target_schema}"
    sql = f"""{header}
    CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
        '{target_location}',
        $$
{inner_yaml.rstrip()}
        $$,
        FALSE
    );"""
    return sql


def generate_sql(semantic_assets_path: str | Path) -> str:
    assets = load_semantic_assets(semantic_assets_path)
    source = assets.get("source", {})
    target = assets.get("target", {})
    source_database = source.get("database", "")
    source_schema = source.get("schema", "")
    target_database = target.get("database", "")
    target_schema = target.get("schema", "")
    if not source_database or not source_schema:
        raise GenerateSQLError("Missing source database/schema in semantic_assets")
    if not target_database or not target_schema:
        raise GenerateSQLError("Missing target database/schema in semantic_assets")
    semantic_assets = assets.get("semantic_assets", [])
    if not semantic_assets:
        raise GenerateSQLError("No semantic assets found")
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_file = assets.get("source_file", "")
    lines = [
        "-- AUTO-GENERATED SEMANTIC VIEW SQL",
        f"-- Generated at: {generated_at}",
        f"-- Source: {source_file}",
        "",
    ]
    for asset in semantic_assets:
        sql = generate_sql_statement(
            asset, source_database, source_schema, target_database, target_schema
        )
        lines.append(sql)
        lines.append("")
    return "\n".join(lines)


def write_sql(sql: str, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(sql)
