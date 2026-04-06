from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from snowflake.snowpark import Session

from core.snowflake.exec import connect, describe_table
from core.sql_utils import build_fqn, quote_identifier


@dataclass
class ColumnSpec:
    name: str
    type: str
    comment: str | None = None
    synonyms: list[str] = field(default_factory=list)
    glossary: str | None = None
    sample_values: list[str] = field(default_factory=list)


@dataclass
class TableSpec:
    columns: list[ColumnSpec] = field(default_factory=list)
    row_count: int | None = None
    primary_keys: list[str] = field(default_factory=list)
    foreign_keys: list[str] = field(default_factory=list)


@dataclass
class JoinSpec:
    table: str
    join_to: str
    left_key: str
    right_key: str
    join_type: str = "left"


@dataclass
class SemanticViewSpec:
    name: str
    domains: list[str]
    base_tables: list[str]
    joins: list[JoinSpec] = field(default_factory=list)
    description: str = ""


@dataclass
class SourceTarget:
    database: str
    schema: str


@dataclass
class EnrichedSpec:
    version: str
    generated_at: str
    source_file: str
    enriched_at: str
    source: SourceTarget
    target: SourceTarget
    tables: dict[str, TableSpec]
    semantic_views: list[SemanticViewSpec]


class EnrichError(Exception):
    pass


def load_raw_spec(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise EnrichError(f"Raw spec file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_table_names(raw_spec: dict[str, Any]) -> set[str]:
    tables = set()
    for sv in raw_spec.get("semantic_views", []):
        base_tables = sv.get("base_tables", [])
        if not base_tables:
            base_table = sv.get("base_table")
            if base_table:
                tables.add(base_table)
        else:
            for bt in base_tables:
                tables.add(bt)
        for join in sv.get("joins", []):
            table = join.get("table")
            if table:
                tables.add(table)
    return tables


def fetch_table_metadata(
    session: Session,
    database: str,
    schema: str,
    table_names: set[str],
    fetch_samples: bool = True,
    sample_limit: int = 5,
) -> dict[str, TableSpec]:
    tables = {}
    for table_name in sorted(table_names):
        try:
            columns = describe_table(session, database, schema, table_name)
            sample_values_map = {}
            if fetch_samples:
                sample_values_map = _fetch_sample_values(
                    session,
                    database,
                    schema,
                    table_name,
                    [col.name for col in columns],
                    sample_limit,
                )
            row_count = _fetch_row_count(session, database, schema, table_name)
            primary_keys, foreign_keys = _fetch_constraints(session, database, schema, table_name)
            tables[table_name] = TableSpec(
                columns=[
                    ColumnSpec(
                        name=col.name,
                        type=col.type,
                        comment=col.comment,
                        sample_values=sample_values_map.get(col.name, []),
                    )
                    for col in columns
                ],
                row_count=row_count,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
            )
        except Exception as e:
            raise EnrichError(
                f"Failed to describe table {database}.{schema}.{table_name}: {e}"
            ) from e
    return tables


def _fetch_row_count(
    session: Session,
    database: str,
    schema: str,
    table_name: str,
) -> int | None:
    fqn = build_fqn(database, schema, table_name)
    try:
        result = session.sql(f"SELECT COUNT(*) AS CNT FROM {fqn}").collect()
        if result:
            return int(result[0]["CNT"])
    except Exception:
        pass
    return None


def _fetch_constraints(
    session: Session,
    database: str,
    schema: str,
    table_name: str,
) -> tuple[list[str], list[str]]:
    primary_keys: list[str] = []
    foreign_keys: list[str] = []
    try:
        pk_rows = session.sql(
            f"SHOW PRIMARY KEYS IN {build_fqn(database, schema, table_name)}"
        ).collect()
        for row in pk_rows:
            col = row.get("column_name") or row.get("COLUMN_NAME", "")
            if col and col not in primary_keys:
                primary_keys.append(col)
    except Exception:
        pass
    try:
        fk_rows = session.sql(
            f"SHOW IMPORTED KEYS IN {build_fqn(database, schema, table_name)}"
        ).collect()
        for row in fk_rows:
            col = row.get("fk_column_name") or row.get("FK_COLUMN_NAME", "")
            if col and col not in foreign_keys:
                foreign_keys.append(col)
    except Exception:
        pass
    return primary_keys, foreign_keys


def _fetch_sample_values(
    session: Session,
    database: str,
    schema: str,
    table_name: str,
    column_names: list[str],
    limit: int = 5,
) -> dict[str, list[str]]:
    if not column_names:
        return {}
    full_table_name = build_fqn(database, schema, table_name)
    select_parts = []
    for col_name in column_names:
        quoted_col = quote_identifier(col_name, "column")
        alias = quote_identifier(f"{col_name}_samples", "column")
        select_parts.append(f"APPROX_TOP_K({quoted_col}, {limit}) AS {alias}")
    query = f"SELECT {', '.join(select_parts)} FROM {full_table_name}"
    try:
        result = session.sql(query).collect()
        if not result:
            return {}
        row = result[0]
        sample_values_map = {}
        for col_name in column_names:
            col_key = f"{col_name}_samples"
            approx_result = row[col_key]
            if approx_result:
                import json

                if isinstance(approx_result, str):
                    parsed = json.loads(approx_result)
                else:
                    parsed = approx_result
                values = []
                for item in parsed:
                    if isinstance(item, dict) and "value" in item:
                        val = item["value"]
                        if val is not None:
                            values.append(str(val))
                    elif isinstance(item, (list, tuple)) and len(item) >= 1:
                        val = item[0]
                        if val is not None:
                            values.append(str(val))
                    elif item is not None:
                        values.append(str(item))
                sample_values_map[col_name] = values
            else:
                sample_values_map[col_name] = []
        return sample_values_map
    except Exception as e:
        import logging

        logging.warning(f"Failed to fetch sample values for {full_table_name}: {e}")
        return {col: [] for col in column_names}


def _merge_excel_metadata(
    tables: dict[str, TableSpec], excel_metadata: Any, domains: list[str]
) -> None:
    from core.parse_excel import get_column_metadata

    for table_name, table_spec in tables.items():
        for col in table_spec.columns:
            for domain in domains:
                col_meta = get_column_metadata(excel_metadata, domain, table_name, col.name)
                if col_meta:
                    if col_meta.description:
                        col.comment = col_meta.description
                    col.synonyms = col_meta.synonyms
                    if col_meta.glossary:
                        col.glossary = col_meta.glossary
                    break


def enrich(
    raw_spec_path: str | Path,
    source_database: str,
    source_schema: str,
    target_database: str,
    target_schema: str,
    connection_name: str = "coco",
    session: Session | None = None,
    excel_metadata_path: str | Path | None = None,
) -> EnrichedSpec:
    raw_spec = load_raw_spec(raw_spec_path)
    table_names = extract_table_names(raw_spec)
    if not table_names:
        raise EnrichError("No tables found in raw_spec")
    if session is None:
        session = connect(connection_name)
    tables = fetch_table_metadata(session, source_database, source_schema, table_names)
    semantic_views = []
    all_domains = set()
    for sv in raw_spec.get("semantic_views", []):
        joins = [
            JoinSpec(
                table=j["table"],
                join_to=j["join_to"],
                left_key=j["left_key"],
                right_key=j["right_key"],
                join_type=j.get("join_type", "left"),
            )
            for j in sv.get("joins", [])
        ]
        domain_value = sv["domain"]
        domains = [domain_value] if isinstance(domain_value, str) else domain_value
        all_domains.update(domains)
        base_tables = sv.get("base_tables", [])
        if not base_tables:
            base_table = sv.get("base_table")
            base_tables = [base_table] if base_table else []
        semantic_views.append(
            SemanticViewSpec(
                name=sv["name"],
                domains=domains,
                base_tables=base_tables,
                joins=joins,
                description=sv.get("description", ""),
            )
        )
    if excel_metadata_path:
        from core.parse_excel import parse_excel

        excel_metadata = parse_excel(excel_metadata_path)
        _merge_excel_metadata(tables, excel_metadata, list(all_domains))
    return EnrichedSpec(
        version=raw_spec.get("version", "1.0"),
        generated_at=raw_spec.get("generated_at", ""),
        source_file=raw_spec.get("source_file", ""),
        enriched_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source=SourceTarget(database=source_database, schema=source_schema),
        target=SourceTarget(database=target_database, schema=target_schema),
        tables=tables,
        semantic_views=semantic_views,
    )


def to_yaml(spec: EnrichedSpec) -> str:
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


def write_yaml(spec: EnrichedSpec, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(to_yaml(spec))
