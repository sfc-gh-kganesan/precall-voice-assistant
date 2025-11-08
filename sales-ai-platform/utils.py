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
        token = os.getenv("SALES_AI_METAORCHESTRATOR_API_TOKEN", "")
        if not token:
            print("Warning: SALES_AI_METAORCHESTRATOR_API_TOKEN not set. Sales AI MetaOrchestrator API token may fail.")
        return token


def get_snowflake_connection():
    """
    Get Snowflake connection.
    https://docs.snowflake.com/en/developer-guide/snowpark-container-services/additional-considerations-services-jobs#using-an-oauth-token-to-execute-sql
    """

    if is_spcs_environment():
        return snowflake.connector.connect(
            host=os.getenv("SNOWFLAKE_HOST"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            token=get_snowflake_token(),
            authenticator="oauth",
        )
    else:
        return snowflake.connector.connect(
            host=os.getenv("SNOWFLAKE_HOST"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            token=get_snowflake_token(),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            authenticator="programmatic_access_token",
            user=os.getenv("SNOWFLAKE_USER"),
        )


def get_snowflake_session() -> Session:
    """
    Get Snowflake session.
    """
    return Session.builder.configs({"connection": get_snowflake_connection()}).getOrCreate()
