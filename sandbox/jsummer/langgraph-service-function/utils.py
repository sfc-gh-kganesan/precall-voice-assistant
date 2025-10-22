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


def unpack_function_request(data: dict | Request) -> list[list]:
    """
    Unpack Snowflake Service Function request body and return the list of input arrays.

    Snowflake sends data in format (example): {
    "data": [
                [0, 10, "Alex", "2014-01-01 16:00:00"],
                [1, 20, "Steve", "2015-01-01 16:00:00"],
                [2, 30, "Alice", "2016-01-01 16:00:00"],
                [3, 40, "Adrian", "2017-01-01 16:00:00"]
            ]
    }

    Returns (example):
    [
        [0, 10, "Alex", "2014-01-01 16:00:00"],
        [1, 20, "Steve", "2015-01-01 16:00:00"],
        [2, 30, "Alice", "2016-01-01 16:00:00"],
        [3, 40, "Adrian", "2017-01-01 16:00:00"]
    ]
    """

    if isinstance(data, Request):
        response = data.json()

    else:
        response = data

    if "data" in response and isinstance(response["data"], list) and len(response["data"]) > 0:
        return response["data"]
    else:
        return response