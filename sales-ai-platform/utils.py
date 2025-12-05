"""
Utilities for Snowflake SPCS service function integration.
"""

import hashlib
import os
from pathlib import Path

import snowflake.connector
from dbos import DBOS
from langgraph.graph.state import CompiledStateGraph
from snowflake.snowpark import Session

CURRENT_GRAPH_VERSION = os.getenv("GRAPH_VERSION", "1.1.1")

_snowflake_raw_conn = None
_snowflake_session = None


def unpack_function_request(data: dict) -> list[list]:
    """
    Unpack Snowflake Service Function batch request.

    Snowflake format: {"data": [[0, "Alice"], [1, "Bob"], ...]}
    Each row: [row_index, arg1, arg2, ...]

    Returns list of rows for processing.
    """
    if "data" in data and isinstance(data["data"], list):
        return data["data"]
    return []


def is_spcs_environment() -> bool:
    """
    Check if running in SPCS environment.
    """
    return Path("/snowflake/session/token").exists()


def get_snowflake_token() -> str:
    """
    Get Snowflake authentication token.

    When running in SPCS, reads from /snowflake/session/token.
    When running locally, reads from SNOWFLAKE_PAT environment variable.

    Returns:
        OAuth token for Snowflake API authentication
    """

    if is_spcs_environment():
        token_path = Path("/snowflake/session/token")
        # Running in SPCS container
        return token_path.read_text().strip()
    else:
        # Running locally - use PAT
        token = os.getenv("SNOWFLAKE_PAT", "")
        if not token:
            print("Warning: SNOWFLAKE_PAT not set. Cortex inference may fail.")
        return token


def get_sales_ai_metaorchestrator_api_token():
    """
    Get Sales AI MetaOrchestrator API token.
    """
    if is_spcs_environment():
        token_path = Path("/sfmnt/sales_ai_metaorchestrator_api_token")
        return token_path.read_text().strip()
    else:
        token = _fetch_sales_ai_metaorchestrator_api_token()
        if not token:
            print("Warning: failed to get Sales AI MetaOrchestrator API token. Sales AI MetaOrchestrator API token may fail.")
        return token


def get_snowflake_connection():
    """
    Get Snowflake connection.
    https://docs.snowflake.com/en/developer-guide/snowpark-container-services/additional-considerations-services-jobs#using-an-oauth-token-to-execute-sql
    """
    global _snowflake_raw_conn
    if _snowflake_raw_conn is None:
        if is_spcs_environment():
            _snowflake_raw_conn = snowflake.connector.connect(
                host=os.getenv("SNOWFLAKE_HOST"),
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                token=get_snowflake_token(),
                authenticator="oauth",
            )
        else:
            _snowflake_raw_conn = snowflake.connector.connect(
                host=os.getenv("SNOWFLAKE_HOST"),
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                token=get_snowflake_token(),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
                authenticator="programmatic_access_token",
                user=os.getenv("SNOWFLAKE_USER"),
            )
    return _snowflake_raw_conn


def get_snowflake_session() -> Session:
    """
    Get Snowflake session.
    """
    global _snowflake_session
    if _snowflake_session is None:
        _snowflake_session = Session.builder.configs({"connection": get_snowflake_connection()}).getOrCreate()
    return _snowflake_session


def compute_eval_id(activity_id: str, owner_id: str, salesforce_account_id: str, graph_version: str) -> str:
    """
    Compute the evaluation ID.
    """
    raw = f"{activity_id}-{owner_id}-{salesforce_account_id}-{graph_version}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


@DBOS.step()
def execute_snowflake_query_sync(query: str):
    """
    Execute a Snowflake query synchronously (blocking).
    This runs in a thread pool via asyncio.to_thread() to avoid blocking
    the event loop, but uses the simple synchronous Snowpark API.
    Returns:
        tuple: (results, query_id) where results is the query result and
               query_id is the Snowflake query ID for tracking
    """
    session = get_snowflake_session()
    result = session.sql(query)
    rows = result.collect()
    query_id = session.sql("SELECT LAST_QUERY_ID()").collect()[0][0]
    return rows, query_id


async def execute_graph_in_stream(graph: CompiledStateGraph, activity_id: str, owner_id: str, salesforce_account_id: str) -> dict:
    """
    Execute the graph in a stream.
    """
    all_states = {}

    async for event in graph.astream(
        {
            "activity_id": activity_id,
            "owner_id": owner_id,
            "salesforce_account_id": salesforce_account_id,
        },
        stream_mode="updates",
        config={"graph_version": CURRENT_GRAPH_VERSION},
    ):
        all_states.update(event)
    return all_states


def _rotate_token_impl():
    """Helper function to perform the actual token rotation logic."""
    if not is_spcs_environment():
        return True
    token = _fetch_sales_ai_metaorchestrator_api_token()
    if token:
        with open("/sfmnt/sales_ai_metaorchestrator_api_token", "w") as f:
            f.write(token)
        return True
    return False


def _fetch_sales_ai_metaorchestrator_api_token():
    """Helper function to fetch the Sales AI MetaOrchestrator API token."""
    session = get_snowflake_session()
    result = session.sql(f"SELECT SALES.RAVEN_DEV.GET_SALES_AI_AUTH_TOKEN('{os.getenv('METAORCHESTRATOR_AUTH_EMAIL')}'):data:access_token::VARCHAR").collect()
    return result[0][0] if result else None
