"""
FastAPI server that exposes the DDA Agent with streaming capabilities.

This API wraps the PydanticAI agent and provides HTTP endpoints for:
- Streaming query responses
- Listing available tools
- Health checks

Intended for integration with agentsim and other services.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)

from app.agent import create_dda_agent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DDA Agent API",
    description="Streaming API for the DDA troubleshooting agent with Glean integration",
    version="1.0.0",
)

# Enable CORS for agentsim integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance (initialized on startup)
agent = None


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
    dda_server: str
    glean_proxy: str


# Startup event to initialize agent
@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    global agent
    logger.info("Initializing DDA Agent...")

    try:
        agent = create_dda_agent(
            model_name="claude-4-sonnet",
            mcp_server_url="http://localhost:8000/mcp",
            glean_proxy_url="http://localhost:8001/mcp",
        )
        logger.info("✓ Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return HealthResponse(
        status="healthy",
        dda_server="http://localhost:8000/mcp",
        glean_proxy="http://localhost:8001/mcp",
    )


@app.get("/tools")
async def list_tools():
    """
    List all available tools from DDA and Glean.

    Note: This is a simplified version. For full tool schemas,
    you could query the MCP servers directly.
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return {
        "dda_tools": [
            "Case operations (get_case, search_cases, etc.)",
            "Query analysis (metadata, locks, compilation)",
            "TSW diagnostics (UDF, RBAC, auth, incidents)",
            "Warehouse and account operations",
            "JIRA integration",
        ],
        "glean_tools": [
            "search - Search documents and files",
            "code_search - Search internal code repositories",
            "employee_search - Find company employees",
            "read_document - Get full document content by URL",
        ],
    }


@app.post("/query")
async def query_agent(request: QueryRequest):
    """
    Send a query to the agent with optional streaming.

    For streaming responses, returns Server-Sent Events (SSE) with:
    - tool_call: When the agent calls a tool
    - tool_result: When a tool returns results
    - text_delta: Streaming text chunks
    - final: Final complete response

    For non-streaming, returns the complete response.
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    logger.info(f"Received query: {request.message}")

    if request.stream:
        # Streaming response using SSE
        async def event_stream():
            try:
                full_response = ""

                async for event in agent.run_stream_events(request.message):
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
                logger.error(f"Error processing query: {e}")
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
        # Non-streaming response
        try:
            result = await agent.run(request.message)
            return {"content": result.output}
        except Exception as e:
            logger.error(f"Error processing query: {e}")
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
        result = await agent.run(request.message)
        return {"response": result.output}
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Run the API server
    uvicorn.run(
        "app.agent_api:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info",
    )
