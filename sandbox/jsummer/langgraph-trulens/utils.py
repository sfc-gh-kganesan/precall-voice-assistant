import logging
from pathlib import Path
import os
from dotenv import load_dotenv
# from typing import Dict, Union, Optional, Any
# from dataclasses import dataclass


# from snowflake.connector import connect, connection, DictCursor
# from langgraph.runtime import get_runtime
from snowflake.snowpark import Session


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# trulens.connectors.snowflake.SnowflakeConnector requires a DATABASE and SCHEMA to be explicitly set either directly or via snowpark session
DATABASE_NAME = "JSUMMER"
SCHEMA_NAME = "SANDBOX"

def is_running_in_spcs_container() -> bool:
    """
    Check if the application is running inside a Snowflake SPCS (Snowpark Container Services) container.

    Returns
    -------
    bool
        True if running in a Snowflake SPCS container, False otherwise
    """
    token_path = Path("/snowflake/session/token")
    return token_path.exists() and token_path.is_file()


def get_connection_params() -> dict:
    """
    Get the connection parameters for the Snowflake connection.
    """
    try:
        # Check if running in SPCS container
        is_spcs_container = is_running_in_spcs_container()

        # Get connection parameters based on environment
        if is_spcs_container:
            connection_params = {
                "host": os.getenv("SNOWFLAKE_HOST"),
                "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                "token": get_spcs_container_token(),
                "authenticator": "oauth",
                "database": DATABASE_NAME,
                "schema": SCHEMA_NAME,
            }

        else:
            load_dotenv()
            connection_params = {
                "user": os.getenv("SNOWFLAKE_USER"),
                "password": os.getenv("SNOWFLAKE_PAT"),
                "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                "database": DATABASE_NAME,
                "schema": SCHEMA_NAME,
            }

        return connection_params
    except Exception as e:
        logger.error(f"Failed to get connection parameters: {str(e)}")
        raise


def get_spcs_container_token() -> str:
    """
    Read the OAuth token from the SPCS container environment.

    Returns
    -------
    str
        The OAuth token for SPCS container authentication

    Raises
    ------
    FileNotFoundError
        If the token file is not found
    """
    token_path = Path("/snowflake/session/token")
    try:
        with open(token_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        raise


def get_snowpark_session() -> Session:
    """
    Get the Snowpark session.
    """
    try:
        return Session.builder.configs(get_connection_params()).create()
    except Exception as e:
        logger.error(f"Failed to get Snowpark session: {str(e)}")
        raise