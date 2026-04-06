from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

VALID_JOIN_TYPES = {"left", "inner", "right", "full"}
DEFAULT_JOIN_TYPE = "left"


@dataclass
class JoinSpec:
    table: str
    join_to: str
    left_key: str
    right_key: str
    join_type: str = DEFAULT_JOIN_TYPE


@dataclass
class SemanticViewSpec:
    name: str
    domain: str
    base_tables: list[str] = field(default_factory=list)
    joins: list[JoinSpec] = field(default_factory=list)
    description: str = ""


@dataclass
class RawSpec:
    version: str
    generated_at: str
    source_file: str
    semantic_views: list[SemanticViewSpec]


class CSVParseError(Exception):
    pass


def parse_csv(csv_path: str | Path) -> RawSpec:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise CSVParseError(f"CSV file not found: {csv_path}")
    rows = _read_csv(csv_path)
    _validate_rows(rows)
    semantic_views = _group_by_sv(rows)
    return RawSpec(
        version="1.0",
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_file=csv_path.name,
        semantic_views=semantic_views,
    )


def parse_csv_content(content: str, filename: str = "upload.csv") -> RawSpec:
    import io

    rows = []
    reader = csv.DictReader(io.StringIO(content))
    required_headers = {"sv_name", "domain", "table_name", "join_to", "left_key", "right_key"}
    if reader.fieldnames is None:
        raise CSVParseError("CSV file is empty or has no headers")
    actual_headers = set(reader.fieldnames)
    missing = required_headers - actual_headers
    if missing:
        raise CSVParseError(f"Missing required columns: {missing}")
    for i, row in enumerate(reader, start=2):
        row["_line"] = i
        rows.append(row)
    if not rows:
        raise CSVParseError("CSV file has no data rows")
    _validate_rows(rows)
    semantic_views = _group_by_sv(rows)
    return RawSpec(
        version="1.0",
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_file=filename,
        semantic_views=semantic_views,
    )


def _read_csv(csv_path: Path) -> list[dict]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_headers = {"sv_name", "domain", "table_name", "join_to", "left_key", "right_key"}
        if reader.fieldnames is None:
            raise CSVParseError("CSV file is empty or has no headers")
        actual_headers = set(reader.fieldnames)
        missing = required_headers - actual_headers
        if missing:
            raise CSVParseError(f"Missing required columns: {missing}")
        for i, row in enumerate(reader, start=2):
            row["_line"] = i
            rows.append(row)
    if not rows:
        raise CSVParseError("CSV file has no data rows")
    return rows


def _validate_rows(rows: list[dict]) -> None:
    sv_groups: dict[str, list[dict]] = {}
    for row in rows:
        sv_name = row["sv_name"].strip()
        if not sv_name:
            raise CSVParseError(f"Line {row['_line']}: sv_name cannot be empty")
        if sv_name not in sv_groups:
            sv_groups[sv_name] = []
        sv_groups[sv_name].append(row)
    for sv_name, sv_rows in sv_groups.items():
        _validate_semantic_view(sv_name, sv_rows)


def _validate_semantic_view(sv_name: str, rows: list[dict]) -> None:
    base_tables = []
    join_tables = []
    table_names = set()
    for row in rows:
        table_name = row["table_name"].strip()
        join_to = row["join_to"].strip()
        left_key = row["left_key"].strip()
        right_key = row["right_key"].strip()
        join_type_raw = row.get("join_type") or ""
        join_type = join_type_raw.strip().lower() or DEFAULT_JOIN_TYPE
        if not table_name:
            raise CSVParseError(f"Line {row['_line']}: table_name cannot be empty")
        if table_name in table_names:
            raise CSVParseError(
                f"Line {row['_line']}: Duplicate table '{table_name}' in semantic view '{sv_name}'"
            )
        table_names.add(table_name)
        is_base = not join_to and not left_key and not right_key
        is_join = join_to and left_key and right_key
        if not is_base and not is_join:
            raise CSVParseError(
                f"Line {row['_line']}: Invalid row. Either all of (join_to, left_key, right_key) "
                f"must be empty (base table) or all must be provided (join table)"
            )
        if is_join and join_type not in VALID_JOIN_TYPES:
            raise CSVParseError(
                f"Line {row['_line']}: Invalid join_type '{join_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_JOIN_TYPES))}"
            )
        if is_base:
            base_tables.append((table_name, row["_line"]))
        else:
            join_tables.append((table_name, join_to, row["_line"]))
    if len(base_tables) == 0:
        raise CSVParseError(
            f"Semantic view '{sv_name}' has no base table. "
            "At least one row must have empty join_to, left_key, right_key."
        )
    for table_name, join_to, line in join_tables:
        if join_to not in table_names:
            raise CSVParseError(
                f"Line {line}: join_to '{join_to}' references a table not in semantic view '{sv_name}'"
            )


def _group_by_sv(rows: list[dict]) -> list[SemanticViewSpec]:
    sv_groups: dict[str, list[dict]] = {}
    sv_order: list[str] = []
    for row in rows:
        sv_name = row["sv_name"].strip()
        if sv_name not in sv_groups:
            sv_groups[sv_name] = []
            sv_order.append(sv_name)
        sv_groups[sv_name].append(row)
    result = []
    for sv_name in sv_order:
        sv_rows = sv_groups[sv_name]
        base_tables = []
        domain = None
        description = ""
        joins = []
        for row in sv_rows:
            table_name = row["table_name"].strip()
            join_to = row["join_to"].strip()
            if not join_to:
                base_tables.append(table_name)
                if domain is None:
                    domain = row["domain"].strip()
                if not description:
                    description = (row.get("description") or "").strip()
            else:
                join_type = (row.get("join_type") or "").strip().lower() or DEFAULT_JOIN_TYPE
                joins.append(
                    JoinSpec(
                        table=table_name,
                        join_to=join_to,
                        left_key=row["left_key"].strip(),
                        right_key=row["right_key"].strip(),
                        join_type=join_type,
                    )
                )
        result.append(
            SemanticViewSpec(
                name=sv_name,
                domain=domain,
                base_tables=base_tables,
                joins=joins,
                description=description,
            )
        )
    return result


def to_yaml(spec: RawSpec) -> str:
    def spec_to_dict(obj):
        if isinstance(obj, (RawSpec, SemanticViewSpec, JoinSpec)):
            return {k: spec_to_dict(v) for k, v in asdict(obj).items()}
        elif isinstance(obj, list):
            return [spec_to_dict(item) for item in obj]
        else:
            return obj

    data = spec_to_dict(spec)
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def write_yaml(spec: RawSpec, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(to_yaml(spec))
