import logging
from pathlib import Path
import os
from typing import Any
from dataclasses import dataclass

from snowflake.connector import connect
from snowflake.connector import connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ContextSchema:
    connection: connection


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

def get_persistent_connection() -> connection:
    """
    Get a persistent Snowflake connection.

    This method creates a connection that will be kept alive and should be
    explicitly closed when no longer needed.

    Returns
    -------
    connection
        A Snowflake connection object
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
            }

        else:

            connection_params = {
                "user": os.getenv("SNOWFLAKE_USER"),
                "password": os.getenv("SNOWFLAKE_PAT"),
                "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            }

        connection = connect(
            **connection_params,
        )

        return connection

    except Exception as e:
        logger.error(f"Failed to get persistent connection: {str(e)}")
        raise