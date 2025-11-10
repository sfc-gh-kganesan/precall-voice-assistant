"""Cortex Analyst chat agent service using pydantic-ai.

This module provides a chat agent that uses Snowflake Cortex Analyst
for natural language to SQL conversion and data analysis.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Literal

import requests
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import (
    Agent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing_extensions import TypedDict

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Lazy load Snowflake session to avoid import issues at module load time
_snowpark_session = None


def get_snowpark_session():
    """Get or create Snowflake session."""
    global _snowpark_session
    if _snowpark_session is None:
        from snowflake.snowpark import Session

        llm_connection_parameters = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "role": os.getenv("SNOWFLAKE_ROLE"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        }
        _snowpark_session = Session.builder.configs(llm_connection_parameters).create()
    return _snowpark_session


def reset_snowpark_session():
    """Reset the global Snowpark session to force reconnection."""
    global _snowpark_session
    if _snowpark_session:
        try:
            _snowpark_session.close()
        except Exception:
            pass  # Ignore errors closing expired session
    _snowpark_session = None
    logger.info("Snowpark session reset")


class SnowflakeCortexModel(OpenAIChatModel):
    """Custom model that handles Snowflake Cortex API response quirks"""

    async def agent_model(self, function_tools, **kwargs):
        """Override to log what tools are being passed to the API"""
        logger.info("=== LLM REQUEST ===")
        logger.info(f"Number of tools being sent: {len(function_tools) if function_tools else 0}")
        if function_tools:
            for i, tool in enumerate(function_tools):
                logger.info(f"Tool {i}: {tool.get('function', {}).get('name', 'unknown')}")
                logger.info(f"Tool {i} description: {tool.get('function', {}).get('description', 'none')[:100]}...")

        # Call parent implementation
        result = await super().agent_model(function_tools, **kwargs)
        logger.info("=== LLM RESPONSE ===")
        return result

    def _process_response(self, response):
        # Log what the LLM actually returned
        response_dict = response.model_dump()
        if "choices" in response_dict and len(response_dict["choices"]) > 0:
            choice = response_dict["choices"][0]
            if "message" in choice:
                msg = choice["message"]
                logger.info(f"LLM response type: {msg.get('role', 'unknown')}")
                if "tool_calls" in msg and msg["tool_calls"]:
                    logger.info(f"LLM wants to call {len(msg['tool_calls'])} tool(s)")
                    for tc in msg["tool_calls"]:
                        logger.info(f"  - Tool: {tc.get('function', {}).get('name', 'unknown')}")
                else:
                    logger.info("LLM did NOT request any tool calls")
                    logger.info(f"Content preview: {msg.get('content', '')[:100]}...")

        # Patch Snowflake's empty fields before validation
        response_dict = response.model_dump()

        # Fix empty finish_reason
        if "choices" in response_dict:
            for choice in response_dict["choices"]:
                if choice.get("finish_reason") == "":
                    choice["finish_reason"] = "stop"

        # Fix empty service_tier
        if response_dict.get("service_tier") == "":
            response_dict["service_tier"] = "default"

        # Re-create response with fixed data
        from openai.types import chat

        fixed_response = chat.ChatCompletion.model_validate(response_dict)

        # Let parent process the fixed response
        return super()._process_response(fixed_response)


# Setup OpenAI client for Snowflake Cortex
client = AsyncOpenAI(
    max_retries=3,
    api_key=os.getenv("SNOWFLAKE_PASSWORD"),
    base_url=f"https://{os.getenv('SNOWFLAKE_ACCOUNT')}.snowflakecomputing.com/api/v2/cortex/v1",
)

# Create provider and model
provider = OpenAIProvider(openai_client=client)
model = SnowflakeCortexModel("claude-4-sonnet", provider=provider)


# History processor to limit conversation length
async def keep_recent_messages(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep only the last 5 messages to manage token usage and keep context focused."""
    return messages[-5:] if len(messages) > 5 else messages


# Create agent first (without tools)
agent = Agent(
    model,
    system_prompt=(
        "You are a helpful customer support data analyst assistant. When users ask questions about support data, "
        "metrics, cases, or products, you MUST call the query_cortex_analyst tool with their question. The tool will "
        "query the database and return actual data. Use the output of the tool to answer the user's question simply and directly."
    ),
    deps_type=str,
    retries=3,
    history_processors=[keep_recent_messages],
)

logger.info("Agent created")


@agent.tool
async def query_cortex_analyst(ctx, query: str) -> str:
    """Query the support database for metrics, cases, and product information.

    Use this tool whenever the user asks about:
    - Support ticket counts or metrics
    - Product categories or specific products
    - Case data or statistics
    - Any data-related questions

    Args:
        query: The user's natural language question about support data

    Returns:
        Query results from the database as a formatted string
    """
    logger.info(f"=== query_cortex_analyst CALLED with query: {query}")

    # Retry logic for session expiry
    max_retries = 2
    for attempt in range(max_retries):
        try:
            snowpark_session = get_snowpark_session()
            logger.info("Got Snowpark session")

            # Get token from Snowpark session
            token = snowpark_session.connection.rest.token

            analyst_url = f"""https://{os.getenv("SNOWFLAKE_ACCOUNT").replace("_", "-")}.snowflakecomputing.com/api/v2/cortex/analyst/message"""

            # Setup headers with Snowflake authentication
            headers = {
                "Authorization": f'Snowflake Token="{token}"',
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": query,
                            }
                        ],
                    }
                ],
                "semantic_model_file": "@AI_FDE.CX360.CX360/CX_SEMANTIC.yaml",
                "stream": False,
            }

            logger.info(f"Sending request to Cortex Analyst API: {analyst_url}")
            response = requests.post(analyst_url, headers=headers, json=payload)
            logger.info(f"Response status code: {response.status_code}")

            if response.status_code == 200:
                response_json = response.json()
                logger.info(f"Response JSON keys: {response_json.keys()}")

                # Check if this is an error response (has 'error_code' or 'code' keys with string 'message')
                if "error_code" in response_json or ("code" in response_json and isinstance(response_json.get("message"), str)):
                    error_msg = response_json.get("message", "Unknown error")
                    error_code = response_json.get("error_code", response_json.get("code", "UNKNOWN"))
                    logger.error(f"Cortex Analyst Error [{error_code}]: {error_msg}")

                    # Handle session expiry with retry
                    if error_code == "390112":
                        if attempt < max_retries - 1:
                            logger.info(f"Session expired (390112). Resetting session and retrying (attempt {attempt + 1}/{max_retries})")
                            reset_snowpark_session()
                            continue  # Retry with fresh session
                        else:
                            return "⚠️ Database session has expired. Please try your question again."

                    raise Exception(f"Cortex Analyst Error [{error_code}]: {error_msg}")

                # Success response - safely extract content array
                message = response_json.get("message", {})
                if not isinstance(message, dict):
                    logger.error(f"Unexpected message format: {type(message)}")
                    raise Exception("Cortex Analyst returned unexpected message format")

                content = message.get("content", [])
                if not content or not isinstance(content, list):
                    logger.error("Unexpected response format: missing or invalid content array")
                    raise Exception("Cortex Analyst response missing content array")

                # Log the full content array to debug what's being returned
                logger.info(f"Response content array length: {len(content)}")
                for idx, item in enumerate(content):
                    if isinstance(item, dict):
                        logger.info(f"Content item {idx}: type={item.get('type', 'unknown')}, keys={list(item.keys())}")

                # Extract SQL statement from content array
                sql_item = next((item for item in content if isinstance(item, dict) and item.get("type") == "sql"), None)

                if sql_item and "statement" in sql_item:
                    # SQL found - execute it
                    query_sql = sql_item["statement"]
                    logger.info(f"Extracted SQL: {query_sql}")

                    # Execute the SQL query
                    result = snowpark_session.sql(str(query_sql)[:-1]).collect()
                    logger.info(f"SQL execution complete. Row count: {len(result)}")
                    logger.info(f"Result preview: {result[:5] if len(result) > 5 else result}")

                    # Format results as a string for the agent
                    # Convert Snowflake Row objects to JSON-serializable dicts
                    def serialize_value(val):
                        """Convert non-JSON-serializable types to strings."""
                        if isinstance(val, datetime):
                            return val.isoformat()
                        elif hasattr(val, "__str__") and not isinstance(val, (str, int, float, bool, type(None))):
                            return str(val)
                        return val

                    serializable_results = [{k: serialize_value(v) for k, v in row.as_dict().items()} for row in result]
                    result_str = json.dumps(serializable_results, indent=2)
                    logger.info("Returning formatted results to agent")
                    return f"Query executed successfully. Results:\n{result_str}"
                else:
                    # No SQL statement - check for text response
                    logger.info("No SQL statement found, checking for text response")
                    text_item = next((item for item in content if isinstance(item, dict) and item.get("type") == "text"), None)
                    if text_item and "text" in text_item:
                        text_response = text_item["text"]
                        logger.info(f"Cortex Analyst returned text response: {text_response[:100]}...")
                        return f"Cortex Analyst message: {text_response}"
                    else:
                        logger.error(f"No SQL or text found in content array: {content}")
                        raise Exception("Cortex Analyst returned neither SQL nor text response")
            else:
                logger.error(f"Cortex Analyst HTTP Error: {response.status_code} - {response.text}")
                raise Exception(f"Cortex Analyst HTTP Error: {response.status_code} - {response.text}")
        except Exception as e:
            # If this is the last retry, raise the exception
            if attempt >= max_retries - 1:
                raise
            # Otherwise log and continue to next retry
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying...")
            continue


logger.info("Tool 'query_cortex_analyst' registered with agent")


class ChatMessage(TypedDict):
    """Format of messages sent to the browser."""

    role: Literal["user", "model"]
    timestamp: str
    content: str


async def stream_chat_response(prompt: str, message_history: list[ModelMessage] | None = None):
    """
    Stream chat responses from the agent with conversation history support.

    Yields newline-delimited JSON messages containing user prompts and
    model responses. Maintains conversation context using message history.

    Parameters
    ----------
    prompt : str
        User's chat message
    message_history : list[ModelMessage] | None
        Previous conversation messages for context (limited to last 5 by history processor)

    Yields
    ------
    bytes
        Newline-delimited JSON messages with role, timestamp, and content
    """
    logger.info(f"=== stream_chat_response CALLED with prompt: {prompt}")
    logger.info(f"Message history length: {len(message_history) if message_history else 0}")

    # Stream the user prompt so it can be displayed immediately
    yield (
        json.dumps(
            {
                "role": "user",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "content": prompt,
            }
        ).encode("utf-8")
        + b"\n"
    )

    # Run the agent with streaming events to execute tools
    logger.info("Starting agent.run_stream_events with message history")

    # Filter tool messages from history (Snowflake doesn't support them)
    # Only filter PREVIOUS conversation turns, not current execution
    filtered_history = []
    if message_history:
        for msg in message_history:
            # Keep ModelRequest without ToolReturnPart (user messages)
            if isinstance(msg, ModelRequest):
                if not any(isinstance(part, ToolReturnPart) for part in msg.parts):
                    filtered_history.append(msg)
            # Keep ModelResponse without ToolCallPart (assistant text responses)
            elif isinstance(msg, ModelResponse):
                if not any(isinstance(part, ToolCallPart) for part in msg.parts):
                    filtered_history.append(msg)

    logger.info(f"Filtered history length: {len(filtered_history)} (from {len(message_history) if message_history else 0})")

    full_content = ""
    tools_pending = 0

    async for event in agent.run_stream_events(prompt, message_history=filtered_history):
        event_type = type(event).__name__
        logger.info(f"Event: {event_type}, Tools Pending: {tools_pending}")

        # Track tool call start and notify frontend
        if isinstance(event, FunctionToolCallEvent):
            tools_pending += 1
            # Tool name is nested in event.part
            tool_name = getattr(event.part, "tool_name", "unknown")
            logger.info(f"  - Tool call started: {tool_name}")
            yield (
                json.dumps(
                    {
                        "role": "tool_status",
                        "event_type": "tool_call",
                        "timestamp": datetime.now(tz=UTC).isoformat(),
                        "tool_name": tool_name,
                        "status": "running",
                    }
                ).encode("utf-8")
                + b"\n"
            )
            continue

        # Track tool call completion, notify frontend, and reset accumulator when all tools are done
        if isinstance(event, FunctionToolResultEvent):
            tools_pending -= 1
            # Tool name is nested in event.result
            tool_name = getattr(event.result, "tool_name", "unknown")
            logger.info(f"  - Tool call completed: {tool_name}, {tools_pending} tools remaining")

            yield (
                json.dumps(
                    {
                        "role": "tool_status",
                        "event_type": "tool_result",
                        "timestamp": datetime.now(tz=UTC).isoformat(),
                        "tool_name": tool_name,
                        "status": "completed",
                    }
                ).encode("utf-8")
                + b"\n"
            )

            # When ALL tools are done, reset the accumulator for the final answer
            if tools_pending == 0:
                logger.info("  - ALL TOOLS COMPLETED - RESETTING ACCUMULATOR")
                full_content = ""
            continue

        # Extract initial text content from PartStartEvent
        if isinstance(event, PartStartEvent):
            # Defensively check if part has content attribute (could be TextPart, ToolCallPart, etc.)
            if hasattr(event.part, "content"):
                text_content = event.part.content
                if isinstance(text_content, str) and text_content:
                    full_content += text_content
                    logger.info(f"  - extracted from part: '{text_content[:50] if len(text_content) > 50 else text_content}...'")
                    logger.info(f"ACCUMULATED CONTENT (length={len(full_content)}): '{full_content[:100]}...'")
                    yield (
                        json.dumps(
                            {
                                "role": "model",
                                "timestamp": datetime.now(tz=UTC).isoformat(),
                                "content": full_content,
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )

        # Extract text content from PartDeltaEvent
        if isinstance(event, PartDeltaEvent):
            # Check if the delta is a TextPartDelta
            if isinstance(event.delta, TextPartDelta):
                text_content = event.delta.content_delta
                if text_content:
                    full_content += text_content
                    logger.info(f"  - extracted from delta: '{text_content[:50] if len(text_content) > 50 else text_content}...'")
                    logger.info(f"ACCUMULATED CONTENT (length={len(full_content)}): '{full_content[:100]}...'")
                    yield (
                        json.dumps(
                            {
                                "role": "model",
                                "timestamp": datetime.now(tz=UTC).isoformat(),
                                "content": full_content,
                            }
                        ).encode("utf-8")
                        + b"\n"
                    )

        # Check for final result event containing the complete message history
        # Note: Using string-based check because the actual runtime event is AgentRunResultEvent
        event_type_name = type(event).__name__
        if event_type_name == "AgentRunResultEvent":
            logger.info("Received AgentRunResultEvent")
            # The event contains the result object with access to all messages
            result = event.result
            logger.info(f"Result has {len(result.all_messages())} total messages")

            # Send the updated message history to frontend
            messages_json = result.all_messages_json().decode("utf-8")
            yield (
                json.dumps(
                    {
                        "role": "history_update",
                        "timestamp": datetime.now(tz=UTC).isoformat(),
                        "messages": messages_json,
                    }
                ).encode("utf-8")
                + b"\n"
            )
            logger.info("Sent message history update to frontend")

    logger.info(f"Agent events completed. Final content length: {len(full_content)}")


# ============================================================================
# DATABASE FUNCTIONS - COMMENTED OUT FOR SIMPLE VERSION
# Uncomment these to enable chat history persistence in Snowflake
# ============================================================================

# from contextlib import asynccontextmanager
# from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter, ModelRequest, UnexpectedModelBehavior, UserPromptPart
# from fastapi.responses import Response
#
# @asynccontextmanager
# async def lifespan(_app: fastapi.FastAPI):
#     """Manage Snowflake session lifecycle."""
#     # Ensure chat history table exists
#     try:
#         snowpark_session.sql("""
#             CREATE TABLE IF NOT EXISTS AI_FDE.CX360.CHAT_HISTORY (
#                 ID INTEGER AUTOINCREMENT PRIMARY KEY,
#                 TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
#                 MESSAGE_LIST VARIANT
#             )
#         """).collect()
#     except Exception as e:
#         print(f"Warning: Could not create chat history table: {e}")
#
#     yield {'session': snowpark_session}
#
#     # Cleanup
#     try:
#         snowpark_session.close()
#     except Exception:
#         pass
#
# def to_chat_message(m: ModelMessage) -> ChatMessage:
#     """Convert ModelMessage to ChatMessage format."""
#     first_part = m.parts[0]
#     if isinstance(m, ModelRequest):
#         if isinstance(first_part, UserPromptPart):
#             assert isinstance(first_part.content, str)
#             return {
#                 'role': 'user',
#                 'timestamp': first_part.timestamp.isoformat(),
#                 'content': first_part.content,
#             }
#     elif isinstance(m, ModelResponse):
#         if isinstance(first_part, TextPart):
#             return {
#                 'role': 'model',
#                 'timestamp': m.timestamp.isoformat(),
#                 'content': first_part.content,
#             }
#     raise UnexpectedModelBehavior(f'Unexpected message type for chat app: {m}')
#
#
# async def get_messages_from_snowflake() -> list[ModelMessage]:
#     """Retrieve chat history from Snowflake table."""
#     try:
#         result = snowpark_session.sql("""
#             SELECT MESSAGE_LIST
#             FROM AI_FDE.CX360.CHAT_HISTORY
#             ORDER BY ID
#         """).collect()
#
#         messages: list[ModelMessage] = []
#         for row in result:
#             message_json = json.dumps(row['MESSAGE_LIST'])
#             messages.extend(ModelMessagesTypeAdapter.validate_json(message_json))
#         return messages
#     except Exception as e:
#         print(f"Error retrieving messages: {e}\"")
#         return []
#
#
# async def add_messages_to_snowflake(messages: bytes):
#     """Add new messages to Snowflake chat history table."""
#     try:
#         # Parse messages JSON
#         messages_str = messages.decode('utf-8')
#
#         # Insert into Snowflake
#         snowpark_session.sql("""
#             INSERT INTO AI_FDE.CX360.CHAT_HISTORY (MESSAGE_LIST)
#             SELECT PARSE_JSON(?)
#         """, params=[messages_str]).collect()
#     except Exception as e:
#         print(f"Error saving messages: {e}")
