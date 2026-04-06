from __future__ import annotations

import logging
from dataclasses import dataclass

import yaml as _yaml
from snowflake.snowpark import Session

logger = logging.getLogger(__name__)


@dataclass
class AgentDeployResult:
    retrieval_tool: bool = False
    sql_gen_tool: bool = False
    sql_exec_tool: bool = False
    agent: bool = False
    errors: list[str] | None = None

    @property
    def success(self) -> bool:
        return self.retrieval_tool and self.sql_gen_tool and self.sql_exec_tool and self.agent


def _exec(session: Session, sql: str) -> None:
    session.sql(sql).collect()


def create_retrieval_tool(
    session: Session,
    database: str,
    schema: str,
    warehouse: str,
    search_service: str,
    procedure_name: str = "RETRIEVAL_TOOL",
) -> None:
    fqn = f'"{database}"."{schema}"."{procedure_name}"'
    svc_ref = f"{database}.{schema}.{search_service}"
    sql = f"""
CREATE OR REPLACE PROCEDURE {fqn}(USER_QUERY STRING, SEMANTIC_LIMIT FLOAT)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
import json

SVC = "{svc_ref}"

def run(session, user_query: str, semantic_limit: float) -> dict:
    try:
        limit = int(semantic_limit) if semantic_limit else 3
        payload = json.dumps({{"query": user_query, "columns": ["SEMANTIC_VIEW_NAME", "DOMAIN", "SEARCH_TEXT"], "limit": limit}})
        escaped_payload = payload.replace("'", "''")
        search_sql = "SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('" + SVC + "', '" + escaped_payload + "') AS RESULTS"
        rows = session.sql(search_sql).collect()
        if not rows:
            return {{"semantic_view_names": "[]", "hits": [], "count": 0}}
        raw = rows[0]["RESULTS"]
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        results_list = parsed.get("results", [])
        sv_names = []
        hits = []
        for r in results_list:
            sv_name = r.get("SEMANTIC_VIEW_NAME", "")
            if sv_name and sv_name not in sv_names:
                sv_names.append(sv_name)
            hits.append({{
                "semantic_view_name": sv_name,
                "domain": r.get("DOMAIN", ""),
                "search_text": r.get("SEARCH_TEXT", "")[:500],
            }})
        return {{
            "semantic_view_names": json.dumps(sv_names),
            "hits": hits,
            "count": len(sv_names),
        }}
    except Exception as e:
        return {{"error": str(e), "semantic_view_names": "[]", "hits": [], "count": 0}}
$$;
"""
    _exec(session, sql)
    logger.info(f"Created retrieval tool: {fqn}")


def create_sql_gen_tool(
    session: Session,
    database: str,
    schema: str,
    warehouse: str,
    model: str,
    procedure_name: str = "SQL_GEN_TOOL",
) -> None:
    fqn = f'"{database}"."{schema}"."{procedure_name}"'
    sql = f"""
CREATE OR REPLACE PROCEDURE {fqn}(USER_QUESTION STRING, SEMANTIC_VIEW_NAMES STRING)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'snowflake-ml-python')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
import json
import re

BANNED_KEYWORDS = [
    "insert", "update", "delete", "merge", "create", "alter", "drop",
    "grant", "revoke", "truncate", "call", "execute", "copy", "put", "get",
]

MODEL = "{model}"
DEFAULT_DB = "{database}"
DEFAULT_SCHEMA = "{schema}"

SQL_GEN_PROMPT = \"\"\"You are an expert Snowflake SQL analyst.
Generate precise, executable SQL queries based on natural language business questions and semantic view definitions.

<critical_rules>
1. ONLY use tables and columns that appear in the semantic views below
2. NEVER hallucinate or invent column names, table names, or relationships
3. ALWAYS use fully qualified names: DATABASE.SCHEMA.TABLE
4. If a question cannot be answered with available data, respond with: "UNABLE_TO_ANSWER: [reason]"
5. Use Snowflake SQL syntax and functions
6. For complex analyses, compose as a single query using CTEs (WITH clauses)
7. Use explicit JOIN syntax with join keys from semantic view relationships
8. Prefer LEFT JOIN when the question implies optional relationships
</critical_rules>

<output_format>
Return a JSON dict with keys 'reasoning' and 'sql':
{{"reasoning": "<explanation>", "sql": "<complete executable Snowflake SQL>"}}
</output_format>

<semantic_views>
{{semantic_views}}
</semantic_views>

<sql_guidelines>
- Use DATE_TRUNC, DATEADD, DATEDIFF for date logic
- "last N days": column >= DATEADD(day, -N, CURRENT_DATE())
- "this year": column >= DATE_TRUNC('year', CURRENT_DATE())
- Include GROUP BY for all non-aggregated columns
- Use ILIKE for case-insensitive text matching
- Use CTEs for multi-step queries
- NEVER use LIMIT inside aggregate functions
</sql_guidelines>

<business_question>
{{user_question}}
</business_question>
\"\"\"

SQL_CORRECTION_PROMPT = \"\"\"You are an expert Snowflake SQL analyst.
A previously generated SQL query failed validation. Fix the error.

<failed_sql>
{{failed_sql}}
</failed_sql>

<error>
{{error}}
</error>

<semantic_views>
{{semantic_views}}
</semantic_views>

<original_question>
{{user_question}}
</original_question>

Return a JSON dict with keys 'reasoning' and 'sql':
{{"reasoning": "<explanation of fix>", "sql": "<corrected executable Snowflake SQL>"}}
\"\"\"


def restrict_sql(sql_text):
    normalized = sql_text.strip()
    if normalized.endswith(";"):
        normalized = normalized[:-1].strip()
    if ";" in normalized:
        return (False, "SQL must contain exactly one statement.")
    lowered = normalized.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return (False, "Only SELECT statements are allowed.")
    for kw in BANNED_KEYWORDS:
        pattern = r"\\b" + re.escape(kw) + r"\\b"
        if re.search(pattern, lowered):
            return (False, f"Disallowed keyword '{{kw}}' detected.")
    return (True, normalized)


def clean_and_parse_response(response):
    clean = re.sub(r'^```json|```$', '', response.strip(), flags=re.MULTILINE).strip()
    try:
        def escape_newlines(match):
            return match.group(1) + match.group(2).replace('\\n', '\\\\n') + match.group(3)
        fixed = re.sub(r'("sql"\\s*:\\s*")(.*?)("(\\s*)\\}})', escape_newlines, clean, flags=re.DOTALL)
        return json.loads(fixed)
    except json.JSONDecodeError:
        try:
            import ast
            return ast.literal_eval(clean.replace('\\n', ' '))
        except:
            return {{"error": "Parse failure", "raw": response}}


def validate_sql(session, sql_text):
    try:
        escaped = sql_text.replace("'", "''")
        result = session.sql(f"SELECT SYSTEM$VALIDATE_QUERY('{{escaped}}')").collect()[0][0]
        parsed = json.loads(result)
        if parsed.get("success", False):
            return (True, None)
        return (False, parsed.get("explanation", "Unknown validation error"))
    except Exception as e:
        return (False, str(e))


def fetch_sv_yamls(session, sv_names, database, schema):
    yamls = []
    for sv_name in sv_names:
        try:
            ref = f"{{database}}.{{schema}}.{{sv_name}}"
            escaped_ref = ref.replace("'", "''")
            result = session.sql(f"SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{{escaped_ref}}')").collect()
            if result:
                yamls.append(result[0][0])
        except Exception:
            pass
    return yamls


def run(session, user_question: str, semantic_view_names: str) -> dict:
    try:
        sv_names = json.loads(semantic_view_names) if semantic_view_names else []
        if not sv_names:
            return {{"error": "No semantic view names provided"}}

        db_schema_parts = sv_names[0].split(".") if "." in sv_names[0] else None
        if db_schema_parts and len(db_schema_parts) >= 2:
            database = db_schema_parts[0].strip('"')
            schema = db_schema_parts[1].strip('"')
            clean_names = [n.split(".")[-1].strip('"') for n in sv_names]
        else:
            database = DEFAULT_DB
            schema = DEFAULT_SCHEMA
            clean_names = [n.strip('"') for n in sv_names]

        sv_yamls = fetch_sv_yamls(session, clean_names, database, schema)
        if not sv_yamls:
            return {{"error": "Could not read YAML from any semantic view"}}

        sv_text = "\\n\\n".join([f"<sv>\\n{{y}}\\n</sv>" for y in sv_yamls])
        prompt = SQL_GEN_PROMPT.replace("{{semantic_views}}", sv_text).replace("{{user_question}}", user_question)

        from snowflake.cortex import Complete
        response = Complete(MODEL, prompt, session=session)
        parsed = clean_and_parse_response(response)

        if "error" in parsed and "sql" not in parsed:
            return parsed

        sql_text = parsed.get("sql", "")
        if not sql_text:
            return {{"error": "LLM did not produce SQL", "raw": str(parsed)}}

        is_safe, safe_result = restrict_sql(sql_text)
        if not is_safe:
            return {{"error": f"SQL safety check failed: {{safe_result}}"}}

        is_valid, validation_error = validate_sql(session, safe_result)
        if is_valid:
            return {{"sql": safe_result, "reasoning": parsed.get("reasoning", "")}}

        correction_prompt = SQL_CORRECTION_PROMPT.replace("{{failed_sql}}", safe_result).replace("{{error}}", validation_error or "").replace("{{semantic_views}}", sv_text).replace("{{user_question}}", user_question)
        retry_response = Complete(MODEL, correction_prompt, session=session)
        retry_parsed = clean_and_parse_response(retry_response)
        retry_sql = retry_parsed.get("sql", "")
        if not retry_sql:
            return {{"error": "Retry did not produce SQL", "original_error": validation_error}}

        is_safe2, safe_result2 = restrict_sql(retry_sql)
        if not is_safe2:
            return {{"error": f"Retry SQL safety check failed: {{safe_result2}}"}}

        is_valid2, validation_error2 = validate_sql(session, safe_result2)
        if is_valid2:
            return {{"sql": safe_result2, "reasoning": retry_parsed.get("reasoning", "")}}

        return {{"error": f"SQL validation failed after retry: {{validation_error2}}", "sql": safe_result2}}
    except Exception as e:
        return {{"error": str(e)}}
$$;
"""
    _exec(session, sql)
    logger.info(f"Created sql_gen tool: {fqn}")


def create_sql_exec_tool(
    session: Session,
    database: str,
    schema: str,
    warehouse: str,
    procedure_name: str = "SQL_EXEC_TOOL",
) -> None:
    fqn = f'"{database}"."{schema}"."{procedure_name}"'
    sql = f"""
CREATE OR REPLACE PROCEDURE {fqn}(SQL_TEXT STRING)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS CALLER
AS
$$
import re

BANNED_KEYWORDS = [
    "insert", "update", "delete", "merge", "create", "alter", "drop",
    "grant", "revoke", "truncate", "call", "execute", "copy", "put", "get",
]

def restrict_sql(sql_text):
    normalized = sql_text.strip()
    if normalized.endswith(";"):
        normalized = normalized[:-1].strip()
    if ";" in normalized:
        return (False, "SQL must contain exactly one statement.")
    lowered = normalized.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return (False, "Only SELECT statements are allowed.")
    for kw in BANNED_KEYWORDS:
        pattern = r"\\b" + re.escape(kw) + r"\\b"
        if re.search(pattern, lowered):
            return (False, f"Disallowed keyword '{{kw}}' detected.")
    return (True, normalized)

def run(session, sql_text: str) -> dict:
    try:
        sql_text = sql_text.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
        is_safe, result = restrict_sql(sql_text)
        if not is_safe:
            return {{"success": False, "error": result, "columns": [], "data": [], "row_count": 0}}
        rows = session.sql(result).collect()
        if rows:
            columns = list(rows[0].as_dict().keys())
            data = [row.as_dict() for row in rows]
        else:
            columns = []
            data = []
        return {{"success": True, "columns": columns, "data": data, "row_count": len(data)}}
    except Exception as e:
        return {{"success": False, "error": str(e), "columns": [], "data": [], "row_count": 0}}
$$;
"""
    _exec(session, sql)
    logger.info(f"Created sql_exec tool: {fqn}")


ORCHESTRATION_TEMPLATE = """You are a data assistant powered by Semantic Forge.
Generate and execute SQL to answer business questions. Follow this workflow exactly.

WORKFLOW:

STEP 1 — RETRIEVE CONTEXT
Call {retrieval_tool}:
  USER_QUERY = "<original question>"
  SEMANTIC_LIMIT = 3

If retrieval fails or returns nothing: inform user, list available domains
({domains}), STOP.

STEP 2 — DETERMINE QUERY STRATEGY
- Single (default): One concept, or compound filters on same entity.
- Parallel: Independent parts joined by "AND", "vs", or comma.
- Sequential: Second part needs a value from the first result.

STEP 3 — GENERATE SQL
Call {sql_gen_tool}:
  USER_QUESTION = "<original question or sub-question>"
  SEMANTIC_VIEW_NAMES = "<from retrieval semantic_view_names — pass exactly as returned>"

CRITICAL: ALWAYS call this tool. Never decide "unable to answer" yourself.
Let {sql_gen_tool} determine answerability. Never write SQL directly.

STEP 4 — EXECUTE SQL
Call {sql_exec_tool}:
  SQL_TEXT = "<SQL from step 3>"

For parallel: call {sql_exec_tool} for all queries in single response.
For sequential: wait for prior result before next call.

STEP 5 — RESPOND
Present results clearly with:
- A direct answer to the question
- Key data points in a formatted table if applicable
- Brief insight or summary
"""

RESPONSE_INSTRUCTIONS = """Format responses for business users:
- Lead with a direct, concise answer
- Use markdown tables for tabular data
- Highlight key numbers in bold
- Keep explanations brief and jargon-free
- If data seems incomplete, note any caveats
- Never expose raw SQL to the user unless asked
"""


def _discover_domains(session: Session, database: str, schema: str, sv_table: str) -> list[str]:
    try:
        fqn = f'"{database}"."{schema}"."{sv_table}"'
        rows = session.sql(f"SELECT DISTINCT DOMAIN FROM {fqn} ORDER BY DOMAIN").collect()
        return [r["DOMAIN"] for r in rows if r["DOMAIN"]]
    except Exception:
        return []


def create_agent(
    session: Session,
    database: str,
    schema: str,
    warehouse: str,
    model: str,
    agent_name: str = "SEMANTIC_FORGE_AGENT",
    retrieval_tool: str = "RETRIEVAL_TOOL",
    sql_gen_tool: str = "SQL_GEN_TOOL",
    sql_exec_tool: str = "SQL_EXEC_TOOL",
    domains: list[str] | None = None,
) -> None:
    agent_fqn = f'"{database}"."{schema}"."{agent_name}"'
    tool_db_schema = f"{database}.{schema}"

    domains_str = ", ".join(domains) if domains else "available domains"
    orch = ORCHESTRATION_TEMPLATE.format(
        retrieval_tool=retrieval_tool,
        sql_gen_tool=sql_gen_tool,
        sql_exec_tool=sql_exec_tool,
        domains=domains_str,
    )

    spec = {
        "models": {"orchestration": model},
        "instructions": {
            "orchestration": orch,
            "response": RESPONSE_INSTRUCTIONS,
        },
        "tools": [
            {
                "tool_spec": {
                    "type": "generic",
                    "name": retrieval_tool,
                    "description": "Searches for relevant semantic views based on a user question. Returns ranked results with semantic view names and metadata. Always call this tool FIRST to identify the right data domains before generating SQL.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "USER_QUERY": {
                                "type": "string",
                                "description": "The user's natural language question to search for relevant context",
                            },
                            "SEMANTIC_LIMIT": {
                                "type": "number",
                                "description": "Number of semantic views to return (default: 3)",
                            },
                        },
                        "required": ["USER_QUERY", "SEMANTIC_LIMIT"],
                    },
                }
            },
            {
                "tool_spec": {
                    "type": "generic",
                    "name": sql_gen_tool,
                    "description": "Generates executable Snowflake SQL to answer a user's natural language business question. Takes a question and list of semantic view names, reads their schemas, and produces validated SQL.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "USER_QUESTION": {
                                "type": "string",
                                "description": "Natural-language business question from the user",
                            },
                            "SEMANTIC_VIEW_NAMES": {
                                "type": "string",
                                "description": "JSON string list of semantic view names exactly as returned by the retrieval tool",
                            },
                        },
                        "required": ["USER_QUESTION", "SEMANTIC_VIEW_NAMES"],
                    },
                }
            },
            {
                "tool_spec": {
                    "type": "generic",
                    "name": sql_exec_tool,
                    "description": "Executes a SQL query and returns results. Only SELECT statements are allowed.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "SQL_TEXT": {
                                "type": "string",
                                "description": "The SQL query to execute",
                            },
                        },
                        "required": ["SQL_TEXT"],
                    },
                }
            },
        ],
        "tool_resources": {
            retrieval_tool: {
                "type": "procedure",
                "identifier": f"{tool_db_schema}.{retrieval_tool}",
                "execution_environment": {"type": "warehouse", "warehouse": warehouse},
            },
            sql_gen_tool: {
                "type": "procedure",
                "identifier": f"{tool_db_schema}.{sql_gen_tool}",
                "execution_environment": {"type": "warehouse", "warehouse": warehouse},
            },
            sql_exec_tool: {
                "type": "procedure",
                "identifier": f"{tool_db_schema}.{sql_exec_tool}",
                "execution_environment": {"type": "warehouse", "warehouse": warehouse},
            },
        },
    }

    spec_yaml = _yaml.dump(spec, default_flow_style=False, sort_keys=False, allow_unicode=True)
    sql = f"CREATE OR REPLACE AGENT {agent_fqn}\nFROM SPECIFICATION\n$$\n{spec_yaml}\n$$;"
    _exec(session, sql)
    logger.info(f"Created agent: {agent_fqn}")


def deploy_agent(
    session: Session,
    database: str,
    schema: str,
    warehouse: str,
    model: str,
    search_service: str,
    sv_table: str = "SEMANTIC_VIEW_METADATA_SEARCH_SRC",
    agent_name: str = "SEMANTIC_FORGE_AGENT",
    retrieval_tool: str = "RETRIEVAL_TOOL",
    sql_gen_tool: str = "SQL_GEN_TOOL",
    sql_exec_tool: str = "SQL_EXEC_TOOL",
) -> AgentDeployResult:
    result = AgentDeployResult(errors=[])

    domains = _discover_domains(session, database, schema, sv_table)

    try:
        create_retrieval_tool(session, database, schema, warehouse, search_service, retrieval_tool)
        result.retrieval_tool = True
    except Exception as e:
        result.errors.append(f"Retrieval tool: {e}")

    try:
        create_sql_gen_tool(session, database, schema, warehouse, model, sql_gen_tool)
        result.sql_gen_tool = True
    except Exception as e:
        result.errors.append(f"SQL gen tool: {e}")

    try:
        create_sql_exec_tool(session, database, schema, warehouse, sql_exec_tool)
        result.sql_exec_tool = True
    except Exception as e:
        result.errors.append(f"SQL exec tool: {e}")

    try:
        create_agent(
            session,
            database,
            schema,
            warehouse,
            model,
            agent_name,
            retrieval_tool,
            sql_gen_tool,
            sql_exec_tool,
            domains=domains,
        )
        result.agent = True
    except Exception as e:
        result.errors.append(f"Agent: {e}")

    return result
