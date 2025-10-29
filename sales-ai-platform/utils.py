"""
Utilities for Snowflake SPCS service function integration.
"""

import os
from pathlib import Path
import snowflake.connector
from snowflake.snowpark import Session

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

def get_snowflake_token() -> str:
    """
    Get Snowflake authentication token.
    
    When running in SPCS, reads from /snowflake/session/token.
    When running locally, reads from SNOWFLAKE_PAT environment variable.
    
    Returns:
        OAuth token for Snowflake API authentication
    """
    token_path = Path("/snowflake/session/token")
    
    if token_path.exists():
        # Running in SPCS container
        return token_path.read_text().strip()
    else:
        # Running locally - use PAT
        token = os.getenv('SNOWFLAKE_PAT', '')
        if not token:
            print("Warning: SNOWFLAKE_PAT not set. Cortex inference may fail.")
        return token

def get_snowflake_connection():
    """
    Get Snowflake connection.
    https://docs.snowflake.com/en/developer-guide/snowpark-container-services/additional-considerations-services-jobs#using-an-oauth-token-to-execute-sql
    """
    return snowflake.connector.connect(
        host = os.getenv('SNOWFLAKE_HOST'),
        account = os.getenv('SNOWFLAKE_ACCOUNT'),
        token = get_snowflake_token(),
        authenticator = 'oauth'
    )

def get_snowflake_session() -> Session:
    """
    Get Snowflake session.
    """
    return Session.builder.configs({"connection": get_snowflake_connection()}).create()