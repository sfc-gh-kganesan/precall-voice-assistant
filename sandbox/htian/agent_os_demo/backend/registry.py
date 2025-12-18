import json
import os

from backend.models import AgentManifest, ListAgentsRequest, ListAgentsResponse
from backend.utils import execute_snowflake_query_sync

DATABASE = os.getenv("BACKEND_SERVICE_DATABASE", "AGENT_OS_DEMO")
SCHEMA = os.getenv("BACKEND_SERVICE_SCHEMA", "PUBLIC")
AGENT_REGISTRY_TABLE = os.getenv("AGENT_REGISTRY_TABLE", "agent_registry")


def build_list_agents_query(request: ListAgentsRequest) -> str:
    query = f"SELECT * FROM {DATABASE}.{SCHEMA}.{AGENT_REGISTRY_TABLE}"
    if request.search_text:
        query += " ORDER BY created_at DESC"
    query += f" LIMIT {request.limit}"
    query += f" OFFSET {request.offset}"
    return query


async def list_agents(request: ListAgentsRequest) -> ListAgentsResponse:
    try:
        query = build_list_agents_query(request)
        rows, query_id = execute_snowflake_query_sync(query)
        return ListAgentsResponse.from_rows(rows, request.limit, request.offset)
    except Exception as e:
        raise Exception(f"Failed to list agents: {e}")


def build_search_agents_query(request: ListAgentsRequest) -> str:
    query = f"SELECT *, VECTOR_COSINE_SIMILARITY(embedding, SNOWFLAKE.CORTEX.EMBED_TEXT_1024('snowflake-arctic-embed-l-v2.0', '{request.search_text}')) AS score FROM {DATABASE}.{SCHEMA}.{AGENT_REGISTRY_TABLE}"
    query += " ORDER BY score DESC"
    query += f" LIMIT {request.limit}"
    query += f" OFFSET {request.offset}"
    return query


async def search_agents(request: ListAgentsRequest) -> ListAgentsResponse:
    try:
        query = build_search_agents_query(request)
        rows, query_id = execute_snowflake_query_sync(query)
        return ListAgentsResponse.from_rows(rows, request.limit, request.offset)
    except Exception as e:
        raise Exception(f"Failed to search agents: {e}")


def build_agent_embedding_text(agent_manifest: AgentManifest) -> str:
    return f"""
    Name: {agent_manifest.name}
    Tags: {", ".join(agent_manifest.tags)}
    Description: {agent_manifest.description}
    """


def build_add_agent_query(agent_manifest: AgentManifest) -> str:
    embedding_text = build_agent_embedding_text(agent_manifest).replace("'", "''")
    escaped_tags = [t.replace("'", "''") for t in agent_manifest.tags]
    tags_sql = ", ".join(f"'{t}'" for t in escaped_tags)

    input_schema_sql = json.dumps(agent_manifest.input_schema)
    output_schema_sql = json.dumps(agent_manifest.output_schema)
    query = f"""INSERT INTO {DATABASE}.{SCHEMA}.{AGENT_REGISTRY_TABLE}
        (agent_id, name, description, version, icon, runtime, entrypoint, tags, input_schema, output_schema, embedding)
        SELECT
        '{agent_manifest.agent_id}',
        '{agent_manifest.name.replace("'", "''")}',
        '{agent_manifest.description.replace("'", "''")}',
        '{agent_manifest.version}',
        NULL,
        '{agent_manifest.runtime}',
        '{agent_manifest.entrypoint}',
        ARRAY_CONSTRUCT({tags_sql}),
        PARSE_JSON('{input_schema_sql}'),
        PARSE_JSON('{output_schema_sql}'),
        SNOWFLAKE.CORTEX.EMBED_TEXT_1024('snowflake-arctic-embed-l-v2.0', '{embedding_text}')
        WHERE NOT EXISTS (SELECT 1 FROM {DATABASE}.{SCHEMA}.{AGENT_REGISTRY_TABLE} WHERE agent_id = '{agent_manifest.agent_id}');"""
    return query


async def add_agent(agent_manifest: AgentManifest) -> str:
    try:
        agent_id = agent_manifest.agent_id
        query = build_add_agent_query(agent_manifest)
        rows, query_id = execute_snowflake_query_sync(query)
        return agent_id
    except Exception as e:
        raise Exception(f"Failed to add agent: {e}")
