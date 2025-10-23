"""
FastAPI application for the Sales AI Platform.

This application exposes multiple LangGraph workflows through REST endpoints
with automatic OpenAPI documentation.

Also provides Snowflake service function endpoints that handle batch requests.
"""

import uvicorn
import asyncio
from contextlib import asynccontextmanager
from typing import Literal, Optional

from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage

from graphs.greeting_workflow import create_graph as create_greeting_graph
from graphs.arithmetic_agent import graph as arithmetic_graph
from utils import unpack_function_request


# ============================================================================
# API Schemas
# ============================================================================

class GreetingRequest(BaseModel):
    """Request model for the greeting workflow."""
    
    name: str = Field(
        ...,
        description="The name of the person to greet",
        examples=["Alice", "Bob"]
    )


class GreetingResponse(BaseModel):
    """Response model for the greeting workflow."""
    
    name: str = Field(
        description="The name that was greeted"
    )
    age: int = Field(
        description="The generated age"
    )
    message: str = Field(
        description="The personalized greeting message"
    )


class ArithmeticRequest(BaseModel):
    """Request model for the arithmetic agent."""
    
    query: str = Field(
        ...,
        description="Natural language arithmetic question",
        examples=[
            "What is 25 + 17?",
            "Multiply 12 by 8, then divide by 3",
            "Calculate (100 + 50) * 2 - 25"
        ]
    )


class ArithmeticResponse(BaseModel):
    """Response model for the arithmetic agent."""
    
    query: str = Field(
        description="The original query"
    )
    answer: str = Field(
        description="The agent's response with the calculation result"
    )
    tool_calls_made: int = Field(
        description="Number of tool calls the agent made"
    )


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(
        description="Error message describing what went wrong"
    )
    detail: Optional[str] = Field(
        default=None,
        description="Additional error details"
    )

# Application metadata
VERSION = "0.1.0"
TITLE = "Sales AI Platform API"
DESCRIPTION = """
## Sales AI Platform

A collection of AI-powered workflows built with LangGraph.

### Available Workflows

* **Greeting Workflow** - Simple workflow that generates personalized greetings
* **Arithmetic Agent** - LLM-powered agent that performs arithmetic operations

### Features

* 🚀 Fast and async
* 📝 Automatic OpenAPI documentation
* 🔒 Type-safe with Pydantic
* 🧩 Modular graph architecture
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: Pre-compile graphs for better performance
    app.state.greeting_graph = create_greeting_graph()
    print("✓ Greeting workflow graph compiled")
    
    app.state.arithmetic_graph = arithmetic_graph
    print("✓ Arithmetic agent graph loaded")
    
    print(f"🚀 {TITLE} v{VERSION} started")
    
    yield
    
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get(
    "/",
    tags=["System"],
    summary="index"
)
async def index():
    return {"message": "Hello, World!"}


# ============================================================================
# Greeting Workflow Endpoint
# ============================================================================

@app.post("/greeting")
async def greeting_workflow(request: Request):
    """
    Generate personalized greetings.
    
    Handles both:
    - Pydantic format: {"name": "Alice"} → GreetingResponse
    - Snowflake batch: {"data": [[0, "Alice"], ...]} → {"data": [[0, result], ...]}
    """
    body = await request.json()
    
    # Check if Snowflake batch format
    if "data" in body and isinstance(body["data"], list):
        inputs = unpack_function_request(body)
        if not inputs:
            return {"error": "No data provided"}
        
        response = []
        if len(inputs) > 10:
            tasks = [app.state.greeting_graph.ainvoke({"name": row[1]}) for row in inputs]
            results = await asyncio.gather(*tasks)
            response = [[inputs[i][0], results[i]] for i in range(len(inputs))]
        else:
            for row in inputs:
                result = await app.state.greeting_graph.ainvoke({"name": row[1]})
                response.append([row[0], result])
        return {"data": response}
    
    # Pydantic format
    try:
        req = GreetingRequest(**body)
        result = await app.state.greeting_graph.ainvoke({"name": req.name})
        return GreetingResponse(
            name=result["name"],
            age=result["age"],
            message=result["response"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Arithmetic Agent Endpoint
# ============================================================================

@app.post("/arithmetic")
async def arithmetic_workflow(request: Request):
    """
    Solve arithmetic problems using an LLM agent.
    
    Handles both:
    - Pydantic format: {"query": "..."} → ArithmeticResponse
    - Snowflake batch: {"data": [[0, "query1"], ...]} → {"data": [[0, result], ...]}
    
    **Note:** Requires OPENAI_API_KEY environment variable.
    """
    body = await request.json()
    
    # Check if Snowflake batch format
    if "data" in body and isinstance(body["data"], list):
        inputs = unpack_function_request(body)
        if not inputs:
            return {"error": "No data provided"}
        
        async def process_row(row_index: int, query: str):
            input_message = HumanMessage(content=query)
            result = await app.state.arithmetic_graph.ainvoke({"messages": [input_message]})
            final_message = result["messages"][-1]
            answer = final_message.content if hasattr(final_message, "content") else str(final_message)
            return [row_index, {"query": query, "answer": answer}]
        
        if len(inputs) > 10:
            tasks = [process_row(row[0], row[1]) for row in inputs]
            response = await asyncio.gather(*tasks)
        else:
            response = []
            for row in inputs:
                result = await process_row(row[0], row[1])
                response.append(result)
        return {"data": response}
    
    # Pydantic format
    try:
        req = ArithmeticRequest(**body)
        input_message = HumanMessage(content=req.query)
        result = await app.state.arithmetic_graph.ainvoke({"messages": [input_message]})
        messages = result["messages"]
        tool_calls_made = sum(1 for msg in messages if hasattr(msg, "tool_calls") and msg.tool_calls)
        final_message = messages[-1]
        answer = final_message.content if hasattr(final_message, "content") else str(final_message)
        return ArithmeticResponse(query=req.query, answer=answer, tool_calls_made=tool_calls_made)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle unexpected exceptions gracefully."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

