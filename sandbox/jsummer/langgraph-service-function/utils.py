from pathlib import Path
from fastapi import Request
from typing import Any

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


def unpack_function_request(data: dict | Request) -> Any:
    """
    Unpack Snowflake Service Function request body and return the single value input.

    Snowflake sends data in format: {"data": [[0, "invoice_id"]]}
    """

    if isinstance(data, Request):
        response = data.json()

    else:
        response = data

    if "data" in response and isinstance(response["data"], list) and len(response["data"]) > 0:
        return response["data"][0][1]
    else:
        return response