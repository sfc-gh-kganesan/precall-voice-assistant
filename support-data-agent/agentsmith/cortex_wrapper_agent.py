"""Cortex Agent Wrapper for AgentSim Testing.

This module provides a FastAPI server that wraps Snowflake Cortex LLM + Analyst
to create an agent compatible with AgentSim's expected interface.
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.providers.openai import OpenAIProvider

# Import shared Snowflake Cortex model
from backend.code_agent.snowflake_cortex_model import SnowflakeCortexModel

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Cortex Agent Wrapper", version="1.0.0")

# Lazy load Snowflake session
_snowpark_session = None


def get_snowpark_session():
    """Get or create Snowflake session."""
    global _snowpark_session
    if _snowpark_session is None:
        from snowflake.snowpark import Session

        connection_parameters = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "role": os.getenv("SNOWFLAKE_ROLE"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        }
        _snowpark_session = Session.builder.configs(connection_parameters).create()
        logger.info("Snowpark session created")
    return _snowpark_session


def reset_snowpark_session():
    """Reset the global Snowpark session to force reconnection."""
    global _snowpark_session
    if _snowpark_session:
        try:
            _snowpark_session.close()
        except Exception:
            pass
    _snowpark_session = None
    logger.info("Snowpark session reset")


# Setup OpenAI client for Snowflake Cortex
client = AsyncOpenAI(
    max_retries=3,
    api_key=os.getenv("SNOWFLAKE_PASSWORD"),
    base_url=f"https://{os.getenv('SNOWFLAKE_ACCOUNT')}.snowflakecomputing.com/api/v2/cortex/v1",
)

# Create provider and model
provider = OpenAIProvider(openai_client=client)
model = SnowflakeCortexModel("claude-4-sonnet", provider=provider)


# Create agent
agent = Agent(
    model,
    system_prompt=(
        "You are a helpful customer support data analyst assistant. "
        "When users ask questions about support data, metrics, cases, or products, "
        "you MUST call the query_cortex_analyst tool with their question. "
        "The tool will query the database and return actual data. "
        "Use the output of the tool to answer the user's question simply and directly. "
        "After answering, ask if the user needs anything else or has follow-up questions."
    ),
    deps_type=str,
    retries=2,
)

logger.info("Pydantic AI agent created")


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
    logger.info(f"query_cortex_analyst called with query: {query}")

    # Retry logic for session expiry
    max_retries = 2
    for attempt in range(max_retries):
        try:
            snowpark_session = get_snowpark_session()

            # Get token from Snowpark session
            token = snowpark_session.connection.rest.token

            analyst_url = f"""https://{os.getenv("SNOWFLAKE_ACCOUNT").replace("_", "-")}.snowflakecomputing.com/api/v2/cortex/analyst/message"""

            # Setup headers with Snowflake authentication
            headers = {
                "Authorization": f'Snowflake Token="{token}"',
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # Note: You'll need to configure your semantic model file path
            # This is a placeholder - update with your actual semantic model
            semantic_model = os.getenv(
                "SEMANTIC_MODEL_FILE", "@AI_FDE.CX360.CX360/CX_SEMANTIC.yaml"
            )

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
                "semantic_model_file": semantic_model,
                "stream": False,
            }

            logger.info(f"Sending request to Cortex Analyst API: {analyst_url}")
            response = requests.post(analyst_url, headers=headers, json=payload)
            logger.info(f"Response status code: {response.status_code}")

            if response.status_code == 200:
                response_json = response.json()

                # Check for error response
                if "error_code" in response_json or (
                    "code" in response_json
                    and isinstance(response_json.get("message"), str)
                ):
                    error_msg = response_json.get("message", "Unknown error")
                    error_code = response_json.get(
                        "error_code", response_json.get("code", "UNKNOWN")
                    )
                    logger.error(f"Cortex Analyst Error [{error_code}]: {error_msg}")

                    # Handle session expiry with retry
                    if error_code == "390112":
                        if attempt < max_retries - 1:
                            logger.info(
                                f"Session expired. Resetting and retrying (attempt {attempt + 1})"
                            )
                            reset_snowpark_session()
                            continue
                        else:
                            return "⚠️ Database session has expired. Please try your question again."

                    raise Exception(f"Cortex Analyst Error [{error_code}]: {error_msg}")

                # Success response - extract content
                message = response_json.get("message", {})
                content = message.get("content", [])

                # Extract SQL statement
                sql_item = next(
                    (
                        item
                        for item in content
                        if isinstance(item, dict) and item.get("type") == "sql"
                    ),
                    None,
                )

                if sql_item and "statement" in sql_item:
                    # SQL found - execute it
                    query_sql = sql_item["statement"]
                    logger.info(f"Executing SQL: {query_sql[:100]}...")

                    # Execute the SQL query
                    result = snowpark_session.sql(str(query_sql)[:-1]).collect()
                    logger.info(f"SQL execution complete. Row count: {len(result)}")

                    # Format results as JSON
                    from datetime import datetime

                    def serialize_value(val):
                        if isinstance(val, datetime):
                            return val.isoformat()
                        elif hasattr(val, "__str__") and not isinstance(
                            val, (str, int, float, bool, type(None))
                        ):
                            return str(val)
                        return val

                    serializable_results = [
                        {k: serialize_value(v) for k, v in row.as_dict().items()}
                        for row in result
                    ]
                    result_str = json.dumps(serializable_results, indent=2)
                    return f"Query executed successfully. Results:\n{result_str}"
                else:
                    # No SQL statement - check for text response
                    text_item = next(
                        (
                            item
                            for item in content
                            if isinstance(item, dict) and item.get("type") == "text"
                        ),
                        None,
                    )
                    if text_item and "text" in text_item:
                        return f"Cortex Analyst message: {text_item['text']}"
                    else:
                        return "Cortex Analyst returned an unexpected response format"
            else:
                raise Exception(f"Cortex Analyst HTTP Error: {response.status_code}")

        except Exception as e:
            if attempt >= max_retries - 1:
                logger.error(f"Query failed after {max_retries} attempts: {str(e)}")
                return f"Error querying database: {str(e)}"
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying...")
            continue


logger.info("Tool 'query_cortex_analyst' registered with agent")


# Request/Response models
class ChatMessage(BaseModel):
    """Message in conversation context."""

    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Request format expected by AgentSim."""

    message: str
    conversation_id: str
    context: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Response format expected by AgentSim."""

    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    completion_signal: Optional[str] = None
    metadata: Dict[str, Any] = {}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint compatible with AgentSim's AgentClient.

    Handles conversation with Cortex LLM + Analyst tool.
    """
    logger.info(f"Received chat request: conversation_id={request.conversation_id}")
    logger.info(f"Message: {request.message}")
    logger.info(f"Context length: {len(request.context) if request.context else 0}")

    try:
        # Convert context to Pydantic AI message format (if provided)
        message_history = []
        if request.context:
            # For now, keep it simple - Pydantic AI will handle the conversation
            # We don't need to convert the full history
            pass

        # Run the agent
        result = await agent.run(request.message, message_history=message_history)

        # Extract the response content from Pydantic AI result
        # AgentRunResult has .output attribute for the response
        response_content = str(result.output)

        # Check if this looks like a final answer
        # Temporarily disabled to test multi-turn conversations
        # Let AgentSim's stop conditions (max_turns) handle conversation ending
        completion_signal = None
        # if any(phrase in response_content.lower() for phrase in ["hope this helps", "is there anything else", "let me know if"]):
        #     completion_signal = "COMPLETED"

        logger.info(f"Agent response: {response_content[:100]}...")

        return ChatResponse(
            content=response_content,
            tool_calls=None,  # Pydantic AI handles tools internally
            completion_signal=completion_signal,
            metadata={"model": "claude-4-sonnet", "tokens": 0},  # Simplified metadata
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return ChatResponse(
            content=f"I encountered an error: {str(e)}. Please try again.",
            completion_signal=None,  # Don't end conversation on error - let user retry
            metadata={"error": str(e)},
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "cortex-wrapper"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
