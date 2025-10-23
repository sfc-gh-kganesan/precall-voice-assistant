"""
Utilities for Snowflake SPCS service function integration.
"""

import os
from pathlib import Path


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

