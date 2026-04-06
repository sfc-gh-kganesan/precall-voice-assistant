from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ColumnAsset:
    name: str
    type: str
    description: str = ""
    synonyms: list[str] = field(default_factory=list)
    glossary: str = ""
    sample_values: list[str] = field(default_factory=list)


@dataclass
class TableAsset:
    name: str
    columns: list[ColumnAsset] = field(default_factory=list)


@dataclass
class JoinCondition:
    left_column: str
    right_column: str


@dataclass
class Relationship:
    left_table: str
    right_table: str
    join_type: str
    on: list[JoinCondition] = field(default_factory=list)


@dataclass
class VerifiedQuery:
    name: str
    question: str
    sql: str


@dataclass
class SemanticAsset:
    name: str
    description: str
    domains: list[str]
    tables: list[TableAsset] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    verified_queries: list[VerifiedQuery] = field(default_factory=list)


@dataclass
class SourceTarget:
    database: str
    schema: str


@dataclass
class SemanticAssetsSpec:
    version: str
    generated_at: str
    source_file: str
    source: SourceTarget
    target: SourceTarget
    semantic_assets: list[SemanticAsset] = field(default_factory=list)


class TransformError(Exception):
    pass


def load_enriched_spec(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise TransformError(f"Enriched spec file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def transform_semantic_view(sv: dict[str, Any], tables: dict[str, Any]) -> SemanticAsset:
    base_tables = sv.get("base_tables", [])
    if not base_tables:
        base_table = sv.get("base_table")
        base_tables = [base_table] if base_table else []
    table_names = set(base_tables)
    for join in sv.get("joins", []):
        table_names.add(join["table"])
    seen_columns: set[str] = set()
    table_assets = []
    for table_name in _order_tables(base_tables, sv.get("joins", []), table_names):
        if table_name not in tables:
            raise TransformError(f"Table '{table_name}' not found in enriched spec")
        table_data = tables[table_name]
        columns = []
        for col in table_data.get("columns", []):
            col_name = col["name"]
            if col_name in seen_columns:
                continue
            seen_columns.add(col_name)
            columns.append(
                ColumnAsset(
                    name=col_name,
                    type=col["type"],
                    description=col.get("comment") or "",
                    synonyms=col.get("synonyms", []),
                    glossary=col.get("glossary") or "",
                    sample_values=col.get("sample_values", []),
                )
            )
        table_assets.append(TableAsset(name=table_name, columns=columns))
    relationships = []
    for join in sv.get("joins", []):
        relationships.append(
            Relationship(
                left_table=join["join_to"],
                right_table=join["table"],
                join_type=join.get("join_type", "left"),
                on=[JoinCondition(left_column=join["left_key"], right_column=join["right_key"])],
            )
        )
    domains = sv.get("domains", [])
    if isinstance(domains, str):
        domains = [domains]
    return SemanticAsset(
        name=sv["name"],
        description=sv.get("description", ""),
        domains=domains,
        tables=table_assets,
        relationships=relationships,
        verified_queries=[],
    )


def _order_tables(
    base_tables: list[str], joins: list[dict[str, Any]], table_names: set[str]
) -> list[str]:
    ordered = list(base_tables)
    for join in joins:
        if join["table"] not in ordered:
            ordered.append(join["table"])
    for table in sorted(table_names):
        if table not in ordered:
            ordered.append(table)
    return ordered


def transform(enriched_spec_path: str | Path) -> SemanticAssetsSpec:
    enriched = load_enriched_spec(enriched_spec_path)
    tables = enriched.get("tables", {})
    semantic_views = enriched.get("semantic_views", [])
    if not semantic_views:
        raise TransformError("No semantic views found in enriched spec")
    semantic_assets = []
    for sv in semantic_views:
        asset = transform_semantic_view(sv, tables)
        semantic_assets.append(asset)
    return SemanticAssetsSpec(
        version=enriched.get("version", "1.0"),
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_file=enriched.get("source_file", ""),
        source=SourceTarget(
            database=enriched.get("source", {}).get("database", ""),
            schema=enriched.get("source", {}).get("schema", ""),
        ),
        target=SourceTarget(
            database=enriched.get("target", {}).get("database", ""),
            schema=enriched.get("target", {}).get("schema", ""),
        ),
        semantic_assets=semantic_assets,
    )


def to_yaml(spec: SemanticAssetsSpec) -> str:
    def spec_to_dict(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {k: spec_to_dict(v) for k, v in asdict(obj).items()}
        elif isinstance(obj, dict):
            return {k: spec_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [spec_to_dict(item) for item in obj]
        else:
            return obj

    data = spec_to_dict(spec)
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def write_yaml(spec: SemanticAssetsSpec, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(to_yaml(spec))
