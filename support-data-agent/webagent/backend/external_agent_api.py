"""
FastAPI server for the External Agent (No DDA Tools)

This API wraps the PydanticAI external agent and provides HTTP endpoints for:
- Streaming query responses
- Listing available tools
- Health checks

Unlike the main agent API, this does NOT have access to customer-specific
diagnostic data (DDA tools). It's designed for external/public-facing scenarios
with built-in PII protection.
"""

import asyncio
import httpx
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from pydantic_ai import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)

from webagent.external_agent import create_external_agent
from app.core.storage import storage

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="External Agent API (No DDA)",
    description="External-facing API with Glean + Documentation search only (NO customer diagnostic tools)",
    version="1.0.0",
)

# Enable CORS for external integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instances (initialized on startup)
agent = None  # Primary: claude-4-sonnet
fallback_agent = None  # Fallback: openai-o4-mini (created lazily on first timeout)


# Request/Response Models
class QueryRequest(BaseModel):
    """
    Flexible request model for agent queries.

    Accepts multiple payload formats from different customer agents:
    - context can be List[str] or List[Dict] (will normalize to strings)
    - Extra fields like conversation_id are accepted but ignored
    """

    message: str
    context: Optional[Union[List[str], List[Dict[str, Any]]]] = None
    stream: bool = False
    conversation_id: Optional[str] = None  # Accept but ignore

    class Config:
        extra = "ignore"  # Ignore any unknown fields

    @field_validator("context", mode="before")
    @classmethod
    def normalize_context(cls, v):
        """
        Normalize context to List[str] format.

        Handles multiple formats:
        - List[str]: Pass through unchanged
        - List[Dict]: Extract 'content' field from each dict
        - None: Return None
        """
        if v is None:
            return None

        if not isinstance(v, list):
            return v

        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Extract content from dict format (e.g., {"role": "user", "content": "...", "tool_calls": []})
                content = item.get("content", "")
                if content:
                    result.append(content)

        return result if result else None


class ToolInfo(BaseModel):
    """Information about an available tool"""

    name: str
    description: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    glean_proxy: str
    dda_tools_enabled: bool


# Startup event to initialize agent
@app.on_event("startup")
async def startup_event():
    """Initialize the external agent on startup"""
    global agent
    logger.info("Initializing External Agent (No DDA)...")

    try:
        agent = create_external_agent(
            model_name="claude-4-sonnet",
            glean_proxy_url="http://glean-proxy:8001/mcp",
        )
        logger.info("✓ External agent initialized successfully")
        logger.info("⚠️  DDA tools are DISABLED for this agent")
    except Exception as e:
        logger.error(f"Failed to initialize external agent: {e}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return HealthResponse(
        status="healthy",
        glean_proxy="http://glean-proxy:8001/mcp",
        dda_tools_enabled=False,  # Always false for external agent
    )


@app.get("/tools")
async def list_tools():
    """
    List all available tools (Glean + Documentation only).

    Note: DDA tools are NOT available in this external-facing agent.
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return {
        "glean_tools": [
            "search - Search documents and files",
            "code_search - Search internal code repositories",
            "employee_search - Find company employees",
            "read_document - Get full document content by URL",
        ],
        "documentation_tools": [
            "search_snowflake_documentation - Search official Snowflake docs",
        ],
        "dda_tools": "DISABLED - This is an external-facing agent with no access to customer diagnostic data",
    }


async def run_agent_with_fallback(
    message: str, conversation_id: str, context: Optional[List[str]] = None
):
    """
    Run external agent with automatic fallback to openai-o4-mini on timeout.

    Now uses internal storage to manage conversation history instead of
    relying on caller-provided context.

    Retry strategy:
    - Attempts 1-2: claude-4-sonnet (primary)
    - Attempts 3-4: openai-o4-mini (fallback via Snowflake Cortex)

    Args:
        message: The user message/query
        conversation_id: Unique identifier for this conversation
        context: DEPRECATED - context is now managed internally via storage

    Returns:
        Agent result object

    Raises:
        Exception: If all 4 attempts fail
    """
    global fallback_agent

    # Load conversation history from storage
    history = await storage.get_history(conversation_id)
    logger.info(
        f"Loaded {len(history)} messages from storage for conversation {conversation_id}"
    )

    for attempt in range(4):  # Total 4 attempts
        try:
            # Switch to fallback model after 2 failures
            if attempt >= 2:
                # Create fallback agent lazily on first use
                if fallback_agent is None:
                    logger.info(
                        "Primary model timed out after 2 attempts, creating openai-o4-mini fallback agent"
                    )
                    try:
                        fallback_agent = create_external_agent(
                            model_name="openai-o4-mini",  # Uses same Snowflake Cortex backend
                            glean_proxy_url="http://glean-proxy:8001/mcp",
                        )
                        logger.info("✓ Fallback agent created successfully")
                    except Exception as e:
                        logger.error(
                            f"Failed to create fallback agent: {e}, continuing with primary"
                        )
                        fallback_agent = None

                current_agent = fallback_agent if fallback_agent else agent
                agent_name = (
                    "openai-o4-mini"
                    if fallback_agent
                    else "claude-4-sonnet (fallback failed)"
                )
            else:
                current_agent = agent
                agent_name = "claude-4-sonnet"

            logger.info(f"Attempt {attempt + 1}/4 with {agent_name}")

            # Attempt the query with history from storage
            result = await current_agent.run(message, message_history=history)

            if attempt > 0:
                logger.info(
                    f"✓ Query succeeded on attempt {attempt + 1} with {agent_name}"
                )

            # Save updated history back to storage (fire-and-forget, don't block response)
            asyncio.create_task(
                storage.save_history(conversation_id, result.all_messages())
            )
            logger.debug(
                f"Queued save of {len(result.all_messages())} messages for conversation {conversation_id}"
            )

            return result  # Success!

        except (TimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning(
                f"Attempt {attempt + 1}/4 failed with {type(e).__name__}: {str(e)[:100]}"
            )
            if attempt == 3:  # Last attempt
                logger.error("All 4 attempts failed, giving up")
                raise  # Re-raise on final failure
            # Exponential backoff: 1s, 2s, 4s
            backoff = 1.0 * (2**attempt)
            logger.info(f"Waiting {backoff}s before retry...")
            await asyncio.sleep(backoff)
        except Exception as e:
            # Non-timeout errors: don't retry, just raise immediately
            logger.error(
                f"Non-retryable error on attempt {attempt + 1}: {type(e).__name__}: {str(e)[:100]}"
            )
            raise


@app.post("/query")
async def query_agent(request: QueryRequest):
    """
    Send a query to the external agent with optional streaming.

    For streaming responses, returns Server-Sent Events (SSE) with:
    - tool_call: When the agent calls a tool
    - tool_result: When a tool returns results
    - text_delta: Streaming text chunks
    - final: Final complete response

    For non-streaming, returns the complete response.
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    # Parse message if it's a JSON string containing description/subject
    message_text = request.message
    try:
        # Try to parse as JSON in case message contains structured data
        import json as json_lib

        parsed = json_lib.loads(request.message)
        if isinstance(parsed, dict) and "description" in parsed and "subject" in parsed:
            # Format as support ticket
            message_text = (
                f"Subject: {parsed['subject']}\n\nDescription: {parsed['description']}"
            )
            logger.info(
                f"Received structured ticket query with subject: {parsed['subject'][:50]}..."
            )
        else:
            logger.info(f"Received query: {request.message[:100]}...")
    except (json_lib.JSONDecodeError, TypeError):
        # Not JSON, use as-is
        logger.info(f"Received query: {request.message[:100]}...")

    if request.stream:
        # Streaming response using SSE
        async def event_stream():
            try:
                full_response = ""

                async for event in agent.run_stream_events(message_text):
                    # Handle tool call events
                    if isinstance(event, FunctionToolCallEvent):
                        yield f"event: tool_call\ndata: {json.dumps({'tool': event.part.tool_name, 'args': event.part.args})}\n\n"

                    # Handle tool result events
                    elif isinstance(event, FunctionToolResultEvent):
                        yield f"event: tool_result\ndata: {json.dumps({'tool': event.result.tool_name, 'status': 'completed'})}\n\n"

                    # Handle text streaming
                    elif isinstance(event, PartStartEvent):
                        if hasattr(event.part, "content"):
                            text_content = event.part.content
                            if isinstance(text_content, str) and text_content:
                                full_response += text_content
                                yield f"event: text_delta\ndata: {json.dumps({'content': text_content})}\n\n"

                    elif isinstance(event, PartDeltaEvent):
                        if isinstance(event.delta, TextPartDelta):
                            text_content = event.delta.content_delta
                            if text_content:
                                full_response += text_content
                                yield f"event: text_delta\ndata: {json.dumps({'content': text_content})}\n\n"

                # Send final complete response
                yield f"event: final\ndata: {json.dumps({'content': full_response})}\n\n"
                logger.info("Query completed successfully")

            except Exception as e:
                logger.error(f"Error processing query: {e}", exc_info=True)
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable buffering in nginx
            },
        )
    else:
        # Non-streaming response with fallback retry logic
        try:
            result = await run_agent_with_fallback(
                message_text,
                conversation_id=request.conversation_id,
                context=request.context,  # Kept for backwards compat, but ignored
            )
            return {"content": result.output}
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/simple")
async def query_agent_simple(request: QueryRequest):
    """
    Simplified non-streaming endpoint that returns just the text response.

    Useful for simple integrations that don't need streaming or detailed events.
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        result = await run_agent_with_fallback(
            request.message,
            conversation_id=request.conversation_id,
            context=None,  # Ignore context, use internal storage
        )
        return {"response": result.output}
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}/history")
async def clear_conversation_history(conversation_id: str):
    """Clear conversation history for a given conversation.

    Useful for starting fresh or managing memory usage.
    """
    await storage.clear_history(conversation_id)
    return {"status": "cleared", "conversation_id": conversation_id}


@app.get("/conversations")
async def list_conversations():
    """List all active conversations with stored history."""
    conversation_ids = await storage.list_conversations()
    return {"conversation_ids": conversation_ids, "count": len(conversation_ids)}


@app.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
    """Get the current history for a conversation.

    Useful for debugging and understanding conversation state.
    """
    history = await storage.get_history(conversation_id)
    return {
        "conversation_id": conversation_id,
        "message_count": len(history),
        "messages": [str(msg) for msg in history],  # Convert to string for JSON
    }


# Voice endpoints
@app.get("/api/v1/voice/available")
async def check_voice_available() -> dict[str, bool]:
    """Check if voice chat feature is available.

    Voice chat requires an OpenAI API key to be configured in the environment.
    This endpoint allows the frontend to determine whether to enable or
    disable the voice features.

    Returns
    -------
    dict
        {"available": true} if OpenAI API key is set, {"available": false} otherwise
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    available = bool(openai_key and openai_key.strip())

    logger.info(f"Voice availability check: {available}")
    return {"available": available}


@app.post("/api/v1/voice/token")
async def generate_voice_token() -> dict[str, str]:
    """Generate an ephemeral token for OpenAI Realtime API connection.

    This endpoint securely generates ephemeral tokens that the frontend
    can use to establish a WebSocket connection to OpenAI's Realtime API.
    The ephemeral token provides time-limited access without exposing the
    main API key to the client.

    Returns
    -------
    dict
        {"token": "ephemeral_token_value"}

    Raises
    ------
    HTTPException
        503 if OpenAI API key is not configured
        500 if token generation fails
    """
    openai_key = os.getenv("OPENAI_API_KEY")

    if not openai_key or not openai_key.strip():
        logger.error("Voice token requested but OPENAI_API_KEY not configured")
        raise HTTPException(
            status_code=503,
            detail="Voice chat is not configured. Please set OPENAI_API_KEY in environment.",
        )

    try:
        logger.info("Generating ephemeral token for voice session")

        # Generate ephemeral token from OpenAI
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "session": {
                        "type": "realtime",
                        "model": "gpt-realtime",
                    },
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    f"OpenAI token generation failed: {response.status_code} - {error_text}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate voice token: {error_text}",
                )

            data = response.json()
            token = data.get("value")

            if not token:
                logger.error("OpenAI response missing token value")
                raise HTTPException(
                    status_code=500, detail="Token generation response missing value"
                )

            logger.info("Ephemeral token generated successfully")
            return {"token": token}

    except httpx.HTTPError as e:
        logger.error(f"HTTP error during token generation: {e}")
        raise HTTPException(
            status_code=500, detail=f"Network error generating voice token: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error generating token: {e}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        ) from e


if __name__ == "__main__":
    import uvicorn

    # Run the external agent API server
    uvicorn.run(
        "webagent.external_agent_api:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info",
    )
