from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml
from snowflake.snowpark import Session

from core.snowflake.exec import connect
from core.sql_utils import escape_string_literal, validate_cortex_model

logger = logging.getLogger(__name__)


class DescribeError(Exception):
    pass


def load_semantic_assets(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise DescribeError(f"Semantic assets file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _format_tables_for_prompt(tables: list[dict[str, Any]]) -> str:
    lines = []
    for table in tables:
        table_name = table.get("name", "")
        lines.append(f"- {table_name}:")
        for col in table.get("columns", []):
            col_name = col.get("name", "")
            col_type = col.get("type", "")
            col_desc = col.get("description", "")
            synonyms = col.get("synonyms", [])
            sample_values = col.get("sample_values", [])
            col_line = f"    - {col_name} ({col_type})"
            if col_desc:
                col_line += f": {col_desc}"
            if synonyms:
                col_line += f" [synonyms: {', '.join(synonyms)}]"
            if sample_values:
                samples_str = ", ".join(f'"{v}"' for v in sample_values[:5])
                col_line += f" [sample values: {samples_str}]"
            lines.append(col_line)
    return "\n".join(lines)


def _format_relationships_for_prompt(relationships: list[dict[str, Any]]) -> str:
    if not relationships:
        return "None"
    lines = []
    for rel in relationships:
        left = rel.get("left_table", "")
        right = rel.get("right_table", "")
        join_type = rel.get("join_type", "left")
        conditions = rel.get("on", [])
        cond_strs = [
            f"{c.get('left_column', '')} = {c.get('right_column', '')}" for c in conditions
        ]
        lines.append(f"- {left} {join_type} join {right} ON {', '.join(cond_strs)}")
    return "\n".join(lines)


def build_description_prompt(asset: dict[str, Any]) -> str:
    sv_name = asset.get("name", "")
    domains = asset.get("domains", [])
    tables = asset.get("tables", [])
    relationships = asset.get("relationships", [])
    tables_formatted = _format_tables_for_prompt(tables)
    relationships_formatted = _format_relationships_for_prompt(relationships)
    prompt = f"""You are a data catalog assistant. Generate a concise description \
for a Snowflake Semantic View.

SEMANTIC VIEW: {sv_name}
DOMAIN: {", ".join(domains)}

TABLES AND COLUMNS:
{tables_formatted}

RELATIONSHIPS:
{relationships_formatted}

INSTRUCTIONS:
1. Write 2-4 sentences maximum
2. State what this semantic view represents and its business purpose
3. Mention the key tables and what they cover at a high level (do NOT list individual columns)
4. Briefly note what types of business questions it can answer
5. Focus on what makes this semantic view DISTINCT from other views
6. Do NOT use generic language that could apply to any semantic view
7. Do NOT add any information not provided above
8. Do NOT include any markdown formatting, headers, or bullet points - write pure prose

OUTPUT:"""
    return prompt


def generate_description(
    session: Session, asset: dict[str, Any], model: str = "openai-gpt-4.1"
) -> str:
    validate_cortex_model(model)
    prompt = build_description_prompt(asset)
    escaped_prompt = escape_string_literal(prompt)
    sql = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{escaped_prompt}')"
    try:
        result = session.sql(sql).collect()
        if result and len(result) > 0:
            description = result[0][0]
            return description.strip()
        else:
            raise DescribeError("Cortex COMPLETE returned empty result")
    except Exception as e:
        raise DescribeError(f"Failed to generate description: {e}") from e


def describe(
    semantic_assets_path: str | Path,
    connection_name: str = "coco",
    session: Session | None = None,
    model: str = "openai-gpt-4.1",
    force: bool = False,
) -> dict[str, Any]:
    assets = load_semantic_assets(semantic_assets_path)
    semantic_assets = assets.get("semantic_assets", [])
    if not semantic_assets:
        raise DescribeError("No semantic assets found")
    if session is None:
        session = connect(connection_name)
    updated_count = 0
    for asset in semantic_assets:
        sv_name = asset.get("name", "")
        existing_desc = asset.get("description", "").strip()
        if existing_desc and not force:
            continue
        try:
            description = generate_description(session, asset, model)
            asset["description"] = description
            updated_count += 1
        except DescribeError as e:
            logger.warning(f"Failed to generate description for {sv_name}: {e}")
    return assets


COLUMN_DESCRIPTION_BATCH_SIZE = 40


def _build_column_description_prompt(
    asset: dict[str, Any], table: dict[str, Any], columns: list[dict[str, Any]]
) -> str:
    sv_name = asset.get("name", "")
    domains = asset.get("domains", [])
    sv_description = asset.get("description", "")
    relationships = asset.get("relationships", [])
    ctx_lines = [f"Semantic View: {sv_name}", f"Domain: {', '.join(domains)}"]
    if sv_description:
        ctx_lines.append(f"SV Description: {sv_description}")
    rel_strs = []
    for rel in relationships:
        left = rel.get("left_table", "")
        right = rel.get("right_table", "")
        join_type = rel.get("join_type", "left")
        rel_strs.append(f"{left} {join_type} join {right}")
    if rel_strs:
        ctx_lines.append(f"Relationships: {'; '.join(rel_strs)}")
    col_lines = [f"- {c.get('name', '')} ({c.get('type', 'VARCHAR')})" for c in columns]
    return f"""You are a data catalog assistant. Generate a one-sentence business description for each column below.

CONTEXT:
{chr(10).join(ctx_lines)}
Table: {table.get("name", "")}

COLUMNS NEEDING DESCRIPTIONS:
{chr(10).join(col_lines)}

RULES:
1. Each description must be exactly one sentence
2. Focus on the business meaning, not technical details
3. Be specific to this domain - avoid generic language
4. Return ONLY valid JSON: {{"COLUMN_NAME": "description", ...}}"""


def _generate_column_descriptions(
    session: Session, prompt: str, model: str = "openai-gpt-4.1"
) -> dict[str, str]:
    validate_cortex_model(model)
    escaped = escape_string_literal(prompt)
    sql = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{escaped}')"
    try:
        result = session.sql(sql).collect()
    except Exception as e:
        logger.warning(f"Cortex COMPLETE call failed for column descriptions: {e}")
        return {}
    if not result or not result[0][0]:
        return {}
    raw = result[0][0].strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {}
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return {}


def describe_columns(
    semantic_assets_path: str | Path,
    connection_name: str = "coco",
    session: Session | None = None,
    model: str = "openai-gpt-4.1",
    force: bool = False,
) -> dict[str, Any]:
    assets = load_semantic_assets(semantic_assets_path)
    semantic_assets = assets.get("semantic_assets", [])
    if not semantic_assets:
        raise DescribeError("No semantic assets found")
    if session is None:
        session = connect(connection_name)
    total_generated = 0
    for asset in semantic_assets:
        for table in asset.get("tables", []):
            cols_needing = [
                c for c in table.get("columns", []) if not c.get("description", "").strip() or force
            ]
            if not cols_needing:
                continue
            for batch_start in range(0, len(cols_needing), COLUMN_DESCRIPTION_BATCH_SIZE):
                batch = cols_needing[batch_start : batch_start + COLUMN_DESCRIPTION_BATCH_SIZE]
                prompt = _build_column_description_prompt(asset, table, batch)
                descriptions = _generate_column_descriptions(session, prompt, model)
                if not descriptions:
                    continue
                for col in batch:
                    desc = descriptions.get(col.get("name", ""), "")
                    if desc:
                        col["description"] = desc
                        total_generated += 1
    return assets


def write_yaml(assets: dict[str, Any], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(assets, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
