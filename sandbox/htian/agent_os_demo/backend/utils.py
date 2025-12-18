import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv
from snowflake.snowpark import Session

load_dotenv()

_snowflake_session = None
_snowflake_connection = None


def is_spcs_environment() -> bool:
    """
    Check if the application is running inside a Snowflake SPCS (Snowpark Container Services) container.
    """
    token_path = Path("/snowflake/session/token")
    return token_path.exists() and token_path.is_file()


def get_snowflake_token() -> str:
    if is_spcs_environment():
        token_path = Path("/snowflake/session/token")
        return token_path.read_text().strip()
    else:
        return os.getenv("SNOWFLAKE_PAT")


def get_snowflake_connection():
    global _snowflake_connection
    if _snowflake_connection is None:
        _create_snowflake_connection()
    return _snowflake_connection


def get_snowflake_session():
    global _snowflake_session
    if _snowflake_session is None:
        _create_snowflake_session()
    return _snowflake_session


def execute_snowflake_query_sync(query: str) -> tuple[list, str]:
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


def _create_snowflake_session():
    global _snowflake_session
    _snowflake_session = Session.builder.configs(
        {"connection": get_snowflake_connection()}
    ).getOrCreate()


def _create_snowflake_connection():
    global _snowflake_connection
    if is_spcs_environment():
        _snowflake_connection = snowflake.connector.connect(
            host=os.getenv("SNOWFLAKE_HOST"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            token=get_snowflake_token(),
            authenticator="oauth",
            warehouse=os.getenv("WAREHOUSE"),
            database=os.getenv("DATABASE"),
            schema=os.getenv("SCHEMA"),
        )
    else:
        _snowflake_connection = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            token=get_snowflake_token(),
            authenticator="programmatic_access_token",
            user=os.getenv("SNOWFLAKE_USER"),
            database=os.getenv("DATABASE"),
            schema=os.getenv("SCHEMA"),
        )
