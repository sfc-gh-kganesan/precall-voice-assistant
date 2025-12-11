import snowflake.connector
import requests
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import config
import sys, os


def get_snowflake_connection(connection=None):
    """Get or create a Snowflake database connection.

    Args:
        connection: Optional existing Snowflake connection to return. If provided,
            this connection is returned as-is without creating a new one.

    Returns:
        snowflake.connector.connection: Active Snowflake connection configured with
            account, user, role, warehouse, database, and schema from config.

    Note:
        Authentication is determined by config.SNOWFLAKE_AUTHENTICATOR:
        - 'oauth': Uses password field with token from config.SNOWFLAKE_TOKEN
        - Other values: Uses the authenticator method specified
    """
    if connection:
        return connection

    conn_params = {
        "account": config.SNOWFLAKE_ACCOUNT,
        "user": config.SNOWFLAKE_USER,
        "role": config.SNOWFLAKE_ROLE,
        "warehouse": config.SNOWFLAKE_WAREHOUSE,
        "database": config.SNOWFLAKE_DATABASE,
        "schema": config.SNOWFLAKE_SCHEMA,
    }

    auth = config.SNOWFLAKE_AUTHENTICATOR.lower()
    token = config.SNOWFLAKE_TOKEN

    if auth == "oauth" and token:
        # conn_params["authenticator"] = "oauth"
        conn_params["password"] = token
    elif auth:
        conn_params["authenticator"] = auth

    print(f"conn_params: {conn_params}")

    return snowflake.connector.connect(**conn_params)


def query_cortex_analyst(question: str, semantic_model: str = None) -> Dict[str, Any]:
    """Query Cortex Analyst with a natural language question.

    Args:
        question: Natural language question to ask the Cortex Analyst.
        semantic_model: Optional stage path to semantic model file (e.g., '@stage/model.yaml').
            Defaults to config.CORTEX_ANALYST_SEMANTIC_MODEL if not provided.

    Returns:
        Dict containing:
            - success (bool): True if query succeeded, False otherwise
            - data (dict): Response data from Cortex Analyst (if success=True)
            - error (str): Error message (if success=False)

    Example:
        >>> result = query_cortex_analyst('What is total revenue?')
        >>> if result['success']:
        ...     print(result['data'])
    """
    model = semantic_model or config.CORTEX_ANALYST_SEMANTIC_MODEL

    try:
        account_locator = config.SNOWFLAKE_ACCOUNT.replace("_", "-").lower()
        account_url = f"https://{account_locator}.snowflakecomputing.com"

        headers = {
            "Authorization": f"Bearer {config.SNOWFLAKE_TOKEN}",
            "Content-Type": "application/json",
        }

        url = f"{account_url}/api/v2/cortex/analyst/message"

        payload = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question}]}
            ],
            "semantic_model_file": model,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=180)

        if response.status_code == 200:
            data = response.json()
            return {"success": True, "data": data}
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def call_cortex_agent(question: str, account_id: str = None) -> Dict[str, Any]:
    """Call a Cortex Agent and stream the response.

    Uses the :run endpoint with Server-Sent Events (SSE) streaming to get agent responses.

    Args:
        question: Natural language question or instruction for the agent.
        account_id: Optional account identifier (currently unused).

    Returns:
        Dict containing:
            - success (bool): True if agent call succeeded, False otherwise
            - status_code (int): HTTP status code (if success=True)
            - data (dict): Agent response with message content (if success=True)
            - error (str): Error message (if success=False)

    Note:
        Agent configuration is read from config.AGENT_DATABASE, config.AGENT_SCHEMA,
        and config.AGENT_NAME. Authentication uses config.SNOWFLAKE_TOKEN.
    """
    try:
        agent_fqn = config.get_agent_fqn()
        account_locator = config.SNOWFLAKE_ACCOUNT.replace("_", "-").lower()
        account_url = f"https://{account_locator}.snowflakecomputing.com"

        headers = {
            "Authorization": f"Bearer {config.SNOWFLAKE_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Use :run endpoint (not /messages)
        url = f"{account_url}/api/v2/databases/{config.AGENT_DATABASE}/schemas/{config.AGENT_SCHEMA}/agents/{config.AGENT_NAME}:run"

        payload = {
            "parent_message_id": "0",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question}]}
            ],
        }

        response = requests.post(
            url, headers=headers, json=payload, timeout=120, stream=True
        )
        response.raise_for_status()

        # Parse Server-Sent Events (SSE) stream
        final_message = None
        current_event_name = None

        for line in response.iter_lines():
            if not line:
                continue

            line_str = line.decode("utf-8")

            # SSE format: "event: eventname" or "data: {json}"
            if line_str.startswith("event: "):
                current_event_name = line_str[7:]
            elif line_str.startswith("data: "):
                data_str = line_str[6:]  # Remove "data: " prefix

                # Check for stream completion
                if data_str == "[DONE]":
                    break

                try:
                    event_data = json.loads(data_str)

                    # Look for "response" event with complete message
                    if current_event_name == "response" and "content" in event_data:
                        final_message = event_data
                        # Don't break - keep reading until [DONE]

                except json.JSONDecodeError:
                    # Skip invalid JSON in stream
                    continue

        if not final_message:
            return {
                "success": False,
                "error": "No complete message received from agent",
            }

        return {
            "success": True,
            "status_code": 200,
            "data": {
                "message": {
                    "role": "agent",
                    "content": final_message.get("content", []),
                }
            },
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Agent API request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def call_cortex_agent2(question: str, account_id: str = None) -> Dict[str, Any]:
    """Alternative Cortex Agent caller with detailed debugging output.

    Similar to call_cortex_agent but uses non-streaming request and includes
    detailed request/response logging for debugging purposes.

    Args:
        question: Natural language question or instruction for the agent.
        account_id: Optional account identifier (currently unused).

    Returns:
        Dict containing:
            - success (bool): True if agent call succeeded, False otherwise
            - status_code (int): HTTP status code
            - data (dict): Agent response (if success=True)
            - error (str): Error message (if success=False)
            - request (dict): Details of the request made (URL, headers, payload)
            - response (dict): Details of the response received (status, headers)

    Note:
        This function prints debug output including payload and response text.
    """
    conn = get_snowflake_connection()

    try:
        agent_fqn = config.get_agent_fqn()
        account_locator = config.SNOWFLAKE_ACCOUNT.replace("_", "-").lower()
        account_url = f"https://{account_locator}.snowflakecomputing.com"

        headers = {
            "Authorization": f"Bearer {config.SNOWFLAKE_TOKEN}",
            "Content-Type": "application/json",
            # "X-Snowflake-Authorization-Token-Type": "OAUTH",
        }

        url = f"{account_url}/api/v2/databases/{config.AGENT_DATABASE}/schemas/{config.AGENT_SCHEMA}/agents/{config.AGENT_NAME}:run"

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": question,
                        }
                    ],
                },
            ],
        }
        print(json.dumps(payload, indent=2))

        response = requests.post(url, headers=headers, json=payload, timeout=120)

        print("📬 ", response.text)

        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "error": response.text if response.status_code != 200 else None,
            "request": {
                "url": url,
                "headers": {k: v for k, v in headers.items() if k != "Authorization"},
                "payload": payload,
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
            },
        }
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return {"success": False, "error": str(e)}


def log_state(
    step_name: str, line_ref: str, inputs: Dict[str, Any], outputs: Dict[str, Any]
):
    """Log workflow state to JSONL file for debugging and auditing.

    Creates a state directory and appends structured log entries to step-specific files.

    Args:
        step_name: Name of the workflow step being logged. Used as filename.
        line_ref: Reference to code location (e.g., 'workflow.py:142').
        inputs: Dictionary of input parameters for this step.
        outputs: Dictionary of output values produced by this step.

    Side Effects:
        - Creates 'state/' directory if it doesn't exist
        - Appends one JSON line to 'state/{step_name}.jsonl'

    Example:
        >>> log_state('query_data', 'main.py:50',
        ...           {'table': 'sales'}, {'rows': 100})
    """
    os.makedirs("state", exist_ok=True)

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "step": step_name,
        "line_ref": line_ref,
        "inputs": inputs,
        "outputs": outputs,
    }

    log_file = f"state/{step_name}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
