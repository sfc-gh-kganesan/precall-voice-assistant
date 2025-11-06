"""
FastAPI application for the Sales AI Platform.

This application exposes multiple LangGraph workflows through REST endpoints
with automatic OpenAPI documentation.

Also provides Snowflake service function endpoints that handle batch requests.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import List, Optional, Tuple

import uvicorn
from dbos import DBOS, DBOSConfig, Queue

# from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# from typing import Literal, Optional
from pydantic import BaseModel, Field

from graphs.post_meeting_workflow import graph as post_meeting_graph
from utils import unpack_function_request

load_dotenv()
# ============================================================================
# API Schemas
# ============================================================================


# Request and Response model for synchronous RPC
class PostMeetingRequest(BaseModel):
    """Request model for the post meeting workflow."""

    activity_id: str = Field(
        ..., description="The activity ID of the call", examples=["1234567890"]
    )
    owner_id: str = Field(
        ..., description="The owner ID of the call", examples=["1234567890"]
    )
    salesforce_account_id: str = Field(
        ...,
        description="The Salesforce account ID of the call",
        examples=["1234567890"],
    )
    # # TODO: Add additional context and metadata
    # additional_context: str = Field(
    #     default="",
    #     description="Additional context for the meeting regarding the account and opportunity"
    # )
    # metadata: dict[str, str] = Field(
    #     default={},
    #     description="Metadata for the call transcript"
    # )


class PostMeetingResponse(BaseModel):
    """Response model for the post meeting workflow."""

    # id: str = Field(
    #     description="A unique ID for this request"
    # )
    # status: Literal["pending", "error", "completed"] = Field(
    #     description="The status of the request"
    # )
    # error_message: str = Field(
    #     description="The error message if the status is 'error'"
    # )
    analysis: dict = Field(description="The analysis of the meeting")
    # created_at: datetime = Field(
    #     description="The timestamp of the request creation"
    # )
    # updated_at: datetime = Field(
    #     description="The timestamp of the request update"
    # )


class GreetingRequest(BaseModel):
    """Request model for the greeting workflow."""

    name: str = Field(
        ..., description="The name of the person to greet", examples=["Alice", "Bob"]
    )


class GreetingResponse(BaseModel):
    """Response model for the greeting workflow."""

    name: str = Field(description="The name that was greeted")
    age: int = Field(description="The generated age")
    message: str = Field(description="The personalized greeting message")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error message describing what went wrong")
    detail: Optional[str] = Field(default=None, description="Additional error details")


# Application metadata
VERSION = "0.1.0"
TITLE = "Sales AI Platform API"
DESCRIPTION = """
## Sales AI Platform

A collection of AI-powered workflows built with LangGraph.

### Available Workflows

* **Post Meeting Workflow** - Workflow that analyzes a call transcript and extracts relevant information

### Features

* 🚀 Fast and async
* 📝 Automatic OpenAPI documentation
* 🔒 Type-safe with Pydantic
* 🧩 Modular graph architecture
"""

config: DBOSConfig = {
    "name": "sales-ai-platform-dbos",
    "system_database_url": os.getenv("DBOS_SYSTEM_DATABASE_URL", ""),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: Pre-compile graphs for better performance
    app.state.post_meeting_graph = post_meeting_graph
    print("✓ Post meeting workflow graph loaded")

    # initialize dbos
    DBOS(config=config)
    DBOS.launch()
    # This queue may run no more than 10 functions concurrently and may not start more than 50 functions per 30 seconds
    app.state.post_meeting_queue = Queue(
        "post_meeting_queue", concurrency=10, limiter={"limit": 50, "period": 30}
    )
    print("✓ DBOS: launched")
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


@app.get("/", tags=["System"], summary="index")
async def index():
    return {"message": "Hello, World!"}


# ============================================================================
# Post-Meeting Workflow Endpoint
# ============================================================================

# @app.post("/post-meeting")
# async def post_meeting_workflow(request: Request):
#     """
#     Analyze a call transcript and extract relevant information.
#     """
#     body = await request.json()
#     req = PostMeetingRequest(**body)
#     result = await app.state.post_meeting_graph.ainvoke({"call_transcript": req.call_transcript, "additional_context": req.additional_context, "metadata": req.metadata})
#     return PostMeetingResponse(id=result["id"], status=result["status"], error_message=result["error_message"], analysis=result["analysis"], created_at=result["created_at"], updated_at=result["updated_at"])


@app.post("/post-meeting")
async def post_meeting_workflow(request: Request):
    """
    Analyze a call transcript and extract relevant information.

    Handles both:
    - Pydantic format: {"call_transcript": "..."} → PostMeetingResponse
    - Snowflake batch: {"data": [[0, "call_transcript1"], ...]} → {"data": [[0, result], ...]}

    **Note:** Requires OPENAI_API_KEY environment variable.
    """
    body = await request.json()

    # Check if Snowflake batch format
    if "data" in body and isinstance(body["data"], list):
        inputs = unpack_function_request(body)
        if not inputs:
            return {"error": "No data provided"}

        async def process_row(
            row_index: int, activity_id: str, owner_id: str, salesforce_account_id: str
        ):
            result = await app.state.post_meeting_graph.ainvoke(
                {
                    "activity_id": activity_id,
                    "owner_id": owner_id,
                    "salesforce_account_id": salesforce_account_id,
                }
            )
            return [row_index, {"analysis": result}]

        if len(inputs) > 10:
            tasks = [process_row(row[0], row[1], row[2], row[3]) for row in inputs]
            response = await asyncio.gather(*tasks)
        else:
            response = []
            for row in inputs:
                result = await process_row(row[0], row[1], row[2], row[3])
                response.append(result)
        return {"data": response}

    # Pydantic format
    try:
        req = PostMeetingRequest(**body)
        result = await app.state.post_meeting_graph.ainvoke(
            {
                "activity_id": req.activity_id,
                "owner_id": req.owner_id,
                "salesforce_account_id": req.salesforce_account_id,
            }
        )
        return PostMeetingResponse(analysis=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Post Meeting Intelligence Scheduler
# Temporary scheduling logic until the Sales AI team can build their own
# ============================================================================


@DBOS.workflow()
async def meetings_durable_workflow(args: PostMeetingRequest):
    # TODO: right now we will fulfill this request using /post-meeting,
    # however in the future this needs to go to the meta intelligence orchestrator API first
    # it will be invoked using a Snowhouse UDF. In turn it will hit the Cortex Agent which will hit /post-meeting
    result = await app.state.post_meeting_graph.ainvoke(
        {
            "activity_id": args.activity_id,
            "owner_id": args.owner_id,
            "salesforce_account_id": args.salesforce_account_id,
        }
    )
    return PostMeetingResponse(analysis=result)


class MeetingsJobsRequest(BaseModel):
    data: List[Tuple[int, PostMeetingRequest]] = Field(
        ...,
        description="""
        Batch of call transcripts in Snowflake service function format. 
        Each row is a list with two elements: [row_index: int, request_payload: dict]. 
        The request_payload is a JSON object matching PostMeetingRequest schema: 
        '{"call_transcript": "SPEAKER 1: ... SPEAKER 2: ..."}'
        """,
        examples=[
            [
                [
                    0,
                    {
                        "call_transcript": "SPEAKER 1: Hello, how are you? SPEAKER 2: I'm fine, thank you."
                    },
                ],
                [
                    1,
                    {
                        "call_transcript": "SPEAKER 1: Let's discuss the proposal. SPEAKER 2: Sounds good."
                    },
                ],
            ]
        ],
    )


@app.post("/v1/meetings/jobs")
async def meetings_jobs(request: MeetingsJobsRequest):
    # TODO: handle deduplication and partitioning based on some request identifier
    result_data = []
    for row in request.data:
        row_index, row_data = row[0], row[1]
        handle = await app.state.post_meeting_queue.enqueue_async(
            meetings_durable_workflow, row_data
        )
        result_data.append(
            [
                row_index,
                {
                    "message": "Successfully enqueued post-meeting intelligence workflow",
                    "workflow_id": handle.get_workflow_id(),
                },
            ]
        )
    return {"data": result_data}


@app.get("/v1/meetings/jobs/{workflow_id}")
async def meetings_job_status(workflow_id: str):
    handle = await DBOS.retrieve_workflow_async(workflow_id)
    status = await handle.get_status()
    return status


# ============================================================================
# Exception Handlers
# ============================================================================


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle unexpected exceptions gracefully."""
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
