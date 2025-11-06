import logging
from pydantic import BaseModel
from pathlib import Path
import os
from typing import Optional, Any, Dict, Union, TypedDict, Literal, NotRequired
from dataclasses import dataclass
from fastapi import Request

from snowflake.connector import connect, connection, DictCursor
from langgraph.runtime import get_runtime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLASS_OPTIONS = ["invoice", "not an invoice"] # TODO - Make ENUM
FRESH_OR_RERUN_OPTIONS = ["fresh", "rerun"] # TODO - Make ENUM


class State(TypedDict):
    classification: NotRequired[Literal[CLASS_OPTIONS[0], CLASS_OPTIONS[1]]]
    target_table: str
    invoice_id: str # SUBMISSION_ID from ticket_metadata table
    relative_path: str
    stage_name: str
    ai_extract_metadata: NotRequired[dict]
    purchase_order_header_metadata: NotRequired[dict | list[dict]]
    purchase_order_line_item_metadata: NotRequired[dict | list[dict]]
    use_existing_ai_extract: NotRequired[bool] = False
    ai_decision: NotRequired[str]
    ai_reasoning: NotRequired[str]
    ai_processed_at: NotRequired[str]


class AIExtractMetadata(BaseModel):
    """Output structure of graph specifically for AI Extract Metadata"""
    model_config = {"extra": "forbid"} # Cortex Model requires additionalProperties to be false
    
    company_name: str
    currency: str
    invoice_date: str
    memo_description: str
    payment_terms: str
    due_date: str
    purchase_order_number: str
    tax_amount: str
    total_amount: str
    vendor_name: str


class AI_Decision_Output(BaseModel):
    """Final output structure of graph for AI Decision"""
    model_config = {"extra": "forbid"} # Cortex Model requires additionalProperties to be false
    
    ai_decision: str
    ai_reasoning: str
    ai_extract_metadata: AIExtractMetadata


@dataclass
class ContextSchema:
    """
    Context schema for LangGraph runtime.

    Snowflake Python connection cannot be serialized as part of State.

    Args:
        connection: Snowflake Python connection
        thread_id: LangGraph Studio passes thread_id automatically
    """
    connection: Optional[Any] = None  # Use Any to avoid Pydantic serialization issues
    thread_id: Optional[str] = None  # LangGraph Studio passes thread_id automatically


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


def get_snowflake_connection() -> tuple[Union[connection,None], bool]:
    """
    Gets a Snowflake Python connection from runtime context or creates a temporary one.

    Returns:
        connection: Snowflake Python connection
        close_connection: Boolean indicating if the connection should be closed
    
    """
    connection = None
    close_connection = False
    
    # Try to get connection from runtime context
    try:
        runtime = get_runtime(ContextSchema)
        connection = runtime.context.connection
    except Exception as e:
        logger.info(f"Could not get connection from runtime: {str(e)}")
        connection = None
    
    # If no connection in context, create a temporary one (for LangGraph Studio)
    if not connection:
        logger.info("No connection in context, creating temporary connection")
        try:
            connection = get_persistent_connection()
            close_connection = True  # We created it, so we should close it
        except Exception as e:
            logger.error(f"Error creating connection: {str(e)}")
            raise e
    
    return connection, close_connection


def run_query(query: str, params: dict = None) -> list[Dict[str, str]]|str:
    """
    Run a query against the database.
    
    Args:
        query: SQL query string with %(name)s placeholders for parameters
        params: Dictionary of parameters to bind to the query
    """

    try:
        connection, close_connection = get_snowflake_connection()
    except Exception as e:
        logger.error(f"Error getting Snowflake connection: {str(e)}")
        return f"Error getting Snowflake connection: {str(e)}"

    try:
        if connection:
            with connection.cursor(DictCursor) as cursor:
    
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                rows = cursor.fetchall()

                return rows
    except Exception as e:
        logger.error(f"Error running query: {str(e)}")
        return f"Error running query: {str(e)}"

    finally:
        # Close connection if we created it temporarily
        if close_connection and connection:
            connection.close()


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