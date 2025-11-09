"""
FastAPI application for the Sales AI Platform.

This application exposes multiple LangGraph workflows through REST endpoints
with automatic OpenAPI documentation.

Also provides Snowflake service function endpoints that handle batch requests.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager

import uvicorn
from dbos import DBOS, DBOSConfig, Queue
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from graphs.post_meeting_workflow import graph as post_meeting_graph
from utils import (
    get_sales_ai_metaorchestrator_api_token,
    get_snowflake_session,
    unpack_function_request,
)

load_dotenv()
# ============================================================================
# API Schemas
# ============================================================================


# Request and Response model for synchronous RPC
class PostMeetingRequest(BaseModel):
    """Request model for the post meeting workflow."""

    activity_id: str = Field(..., description="The activity ID of the call", examples=["1234567890"])
    owner_id: str = Field(..., description="The owner ID of the call", examples=["1234567890"])
    salesforce_account_id: str = Field(
        ...,
        description="The Salesforce account ID of the call",
        examples=["1234567890"],
    )


class PostMeetingResponse(BaseModel):
    """Response model for the post meeting workflow."""

    analysis: dict = Field(description="The analysis of the meeting")


class GreetingRequest(BaseModel):
    """Request model for the greeting workflow."""

    name: str = Field(..., description="The name of the person to greet", examples=["Alice", "Bob"])


class GreetingResponse(BaseModel):
    """Response model for the greeting workflow."""

    name: str = Field(description="The name that was greeted")
    age: int = Field(description="The generated age")
    message: str = Field(description="The personalized greeting message")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error message describing what went wrong")
    detail: str | None = Field(default=None, description="Additional error details")


# Application metadata
VERSION = "0.1.0"
TITLE = "Sales AI Platform API"
DESCRIPTION = """
## Sales AI Platform

A collection of AI-powered workflows built with LangGraph.

### API Versioning

This API uses URL path versioning (e.g., `/v1/`, `/v2/`). All endpoints are versioned
except for health checks and root endpoints. When breaking changes are introduced,
a new version will be released while maintaining backward compatibility for older versions.

Current API version: **v1**
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: Pre-compile graphs for better performance
    app.state.post_meeting_graph = post_meeting_graph
    print("✓ Post meeting workflow graph loaded")

    # Perform initial API token rotation (non-DBOS version for startup)
    _rotate_token_impl()

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

config: DBOSConfig = {
    "name": "sales-ai-platform-dbos",
    "system_database_url": os.getenv("DBOS_SYSTEM_DATABASE_URL", ""),
}

DBOS(fastapi=app, config=config)

# This queue may run no more than 10 functions concurrently and may not start more than 50 functions per 30 seconds
dbos_meetings_jobs_queue = Queue("dbos_meetings_jobs_queue", concurrency=10, limiter={"limit": 50, "period": 30})

# Create v1 API router
v1_router = APIRouter(prefix="/v1", tags=["v1"])


# ============================================================================
# Health & Info Endpoints
# ============================================================================


@app.get("/", tags=["System"], summary="Root endpoint")
async def index():
    """Root endpoint with API information."""
    return {
        "message": "Sales AI Platform API",
        "version": VERSION,
        "api_version": "v1",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"], summary="Health check")
async def health():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy", "version": VERSION, "api_version": "v1"}


@app.get(
    "/healthz",
    tags=["System"],
    summary="Kubernetes health check",
    include_in_schema=False,
)
async def healthz():
    """Kubernetes-style health check endpoint (hidden from docs)."""
    return {"status": "ok"}


# ============================================================================
# Meeting Analysis RPC
# ============================================================================


@v1_router.post("/meetings/analyze", summary="Analyze meeting transcript")
async def meetings_analyze(request: Request):
    """
    Analyze a call transcript and extract relevant information.

    Handles both:
    - Pydantic format: {"call_transcript": "..."} → PostMeetingResponse
    - Snowflake batch: {"data": [[0, "call_transcript1"], ...]} → {"data": [[0, result], ...]}
    """
    body = await request.json()

    # Check if Snowflake batch format
    if "data" in body and isinstance(body["data"], list):
        inputs = unpack_function_request(body)
        if not inputs:
            return {"error": "No data provided"}

        async def process_row(row_index: int, activity_id: str, owner_id: str, salesforce_account_id: str):
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
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Post Meeting Intelligence Scheduler
# Temporary scheduling logic until the Sales AI team can build their own
# ============================================================================


@DBOS.workflow()
async def meetings_durable_workflow(args: PostMeetingRequest):
    """
    Trigger the post-meeting workflow via the Sales AI MetaOrchestrator UDF.

    This workflow calls the TRIGGER_SALES_AI_WORKFLOW UDF which orchestrates the Cortex Agent,
    which in turn will invoke the appropriate downstream services.
    """
    # Get the Sales AI MetaOrchestrator API token
    auth_token = get_sales_ai_metaorchestrator_api_token()

    # Get user email from environment
    user_email = os.getenv("METAORCHESTRATOR_AUTH_EMAIL")
    if not user_email:
        raise ValueError("METAORCHESTRATOR_AUTH_EMAIL environment variable not set")

    # Construct the workflow payload in the format expected by the MetaOrchestrator
    workflow_payload = {
        "workflow_name": "POST_MEETING_TRANSCRIPT",
        "workflow_variant_name": "POST_MEETING_TRANSCRIPT_V2",
        # TODO: make sure call_transcript is excluded via idempotency_keys
        "inputs": {
            "activity_id": args.activity_id,
            "salesforce_account_id": args.salesforce_account_id,
            "owner_id": args.owner_id,
            "call_transcript": "",
        },
        "user_id": user_email,
        "force_refresh": False,
    }

    # Convert payload to JSON string for the UDF
    payload_json = json.dumps(workflow_payload)

    # Get Snowflake session and call the UDF
    session = get_snowflake_session()
    query = f"""
    SELECT SALES.RAVEN_DEV.TRIGGER_SALES_AI_WORKFLOW(
        '{auth_token}',
        PARSE_JSON('{payload_json}')
    )
    """
    results = session.sql(query).collect()

    if not results:
        raise ValueError("No results returned from TRIGGER_SALES_AI_WORKFLOW UDF")

    # Extract the result from the first row and convert to dict
    result = results[0][0]

    # If result is a string (JSON), parse it to dict
    if isinstance(result, str):
        result = json.loads(result)

    # TODO: create a Pydantic model for the result
    return result


class MeetingsJobsRequest(BaseModel):
    data: list[tuple[int, PostMeetingRequest]] = Field(
        ...,
        description="""
        Batch of call transcripts in Snowflake service function format.
        Each row is a list with two elements: [row_index: int, request_payload: PostMeetingRequest].
        """,
        examples=[
            [
                [
                    0,
                    {"activity_id": "", "owner_id": "", "salesforce_account_id": ""},
                ],
                [
                    1,
                    {"activity_id": "", "owner_id": "", "salesforce_account_id": ""},
                ],
            ]
        ],
    )


@v1_router.post("/meetings/jobs", summary="Submit meeting analysis jobs")
async def meetings_jobs(request: MeetingsJobsRequest):
    # TODO: handle deduplication and partitioning based on some request identifier
    result_data = []
    for row in request.data:
        row_index, row_data = row[0], row[1]
        handle = await dbos_meetings_jobs_queue.enqueue_async(meetings_durable_workflow, row_data)
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


@v1_router.get("/meetings/jobs/{workflow_id}", summary="Get meeting job status")
async def meetings_job_status(workflow_id: str):
    """Get the status of a meeting analysis job by workflow ID."""
    handle = await DBOS.retrieve_workflow_async(workflow_id)
    status = await handle.get_status()
    return status


# ============================================================================
# Sales AI MetaOrchestrator API token rotation
# ============================================================================


def _rotate_token_impl():
    """Helper function to perform the actual token rotation logic."""
    return True
    # session = get_snowflake_session()
    # result = session.sql(f"SELECT SALES.RAVEN_DEV.GET_SALES_AI_AUTH_TOKEN('{os.getenv('METAORCHESTRATOR_AUTH_EMAIL')}'):data:access_token::VARCHAR").collect()
    # token = result[0][0] if result else None
    # if token:
    #     with open("/sfmnt/sales_ai_metaorchestrator_api_token", "w") as f:
    #         f.write(token)
    #     return True
    # return False


@DBOS.scheduled("30 */2 * * *")  # crontab syntax to run every 2 hours and 30 minutes (at 30 minutes past every 2nd hour)
@DBOS.workflow()
def rotate_sales_ai_metaorchestrator_api_token():
    """Scheduled workflow to rotate the Sales AI MetaOrchestrator API token."""
    DBOS.logger.info("Rotating Sales AI MetaOrchestrator API token.")
    success = _rotate_token_impl()
    if success:
        DBOS.logger.info("Sales AI MetaOrchestrator API token rotation completed successfully.")
    else:
        DBOS.logger.error("Failed to rotate Sales AI MetaOrchestrator API token.")


# ============================================================================
# Register API Router
# ============================================================================

app.include_router(v1_router)


# ============================================================================
# Exception Handlers
# ============================================================================


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle unexpected exceptions gracefully."""
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(exc)})


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    DBOS.launch()
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
