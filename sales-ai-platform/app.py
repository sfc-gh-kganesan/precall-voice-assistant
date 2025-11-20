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
from datetime import datetime

import uvicorn
from dbos import DBOS, DBOSConfig, Queue
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from graphs.post_meeting_workflow import graph as post_meeting_graph
from utils import (
    get_sales_ai_metaorchestrator_api_token,
    get_snowflake_session,
    is_spcs_environment,
)

load_dotenv()

# ============================================================================
# API Schemas
# ============================================================================


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
    "enable_otlp": True,
    "otlp_traces_endpoints": [os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")],
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


# ============================================================================
# Meeting Analysis RPC
# ============================================================================


class MeetingsAnalyzeRequest(BaseModel):
    data: list[tuple[int, str, str, str]] = Field(
        ...,
        description="""
        Batch of call transcripts in Snowflake service function format.
        Each row is a list with four elements.
        """,
        examples=[
            [
                [
                    0,
                    "activity_id",
                    "owner_id",
                    "salesforce_account_id",
                ],
                [
                    1,
                    "activity_id",
                    "owner_id",
                    "salesforce_account_id",
                ],
            ]
        ],
    )


class MeetingsAnalyzeResponse(BaseModel):
    """Response model for the post meeting workflow."""

    analysis: dict = Field(description="The analysis of the meeting")


@v1_router.post("/meetings/analyze", summary="Analyze meeting transcript")
async def meetings_analyze(request: MeetingsAnalyzeRequest):
    """
    Analyze a call transcript and extract relevant information.
    """

    async def process_row(row_index: int, activity_id: str, owner_id: str, salesforce_account_id: str):
        result = await app.state.post_meeting_graph.ainvoke(
            {
                "activity_id": activity_id,
                "owner_id": owner_id,
                "salesforce_account_id": salesforce_account_id,
            }
        )
        return [row_index, MeetingsAnalyzeResponse(analysis=result)]

    tasks = [process_row(row[0], row[1], row[2], row[3]) for row in request.data]
    response = await asyncio.gather(*tasks)
    return {"data": response}


# ============================================================================
# Meetings Jobs Scheduler
# Temporary scheduling logic until the Sales AI team can build their own
# ============================================================================


class MeetingsJobParams(BaseModel):
    activity_id: str = Field(..., description="The activity ID of the call", examples=["foo"])
    owner_id: str = Field(..., description="The owner ID of the call", examples=["bar"])
    salesforce_account_id: str = Field(
        ...,
        description="The Salesforce account ID of the call",
        examples=["baz"],
    )


@DBOS.step()
def execute_snowflake_query_sync(query: str):
    """
    Execute a Snowflake query synchronously (blocking).
    This runs in a thread pool via asyncio.to_thread() to avoid blocking
    the event loop, but uses the simple synchronous Snowpark API.
    Returns:
        tuple: (results, query_id) where results is the query result and
               query_id is the Snowflake query ID for tracking
    """
    session = get_snowflake_session()
    result = session.sql(query)
    rows = result.collect()
    query_id = session.sql("SELECT LAST_QUERY_ID()").collect()[0][0]
    return rows, query_id


@DBOS.workflow()
async def meetings_durable_workflow(args: MeetingsJobParams):
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
        # TODO: make sure call_transcript is excluded via idempotency_keys or keep it blank
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

    # Build the query
    query = f"""
    SELECT SALES.RAVEN_DEV.TRIGGER_SALES_AI_WORKFLOW(
        '{auth_token}',
        PARSE_JSON('{payload_json}')
    )
    """

    try:
        # Execute query in thread pool to avoid blocking event loop
        # This will block for ~2 minutes, but in a separate thread
        DBOS.logger.info(f"Executing Snowflake query for activity_id: {args.activity_id}")
        results, query_id = await asyncio.to_thread(execute_snowflake_query_sync, query)
        DBOS.logger.info(f"Snowflake query completed with query_id: {query_id}")

    except Exception as e:
        DBOS.logger.error(f"Snowflake query failed: {str(e)}")
        raise ValueError(f"Failed to execute TRIGGER_SALES_AI_WORKFLOW UDF: {str(e)}") from e

    # Validate results
    if not results:
        raise ValueError("No results returned from TRIGGER_SALES_AI_WORKFLOW UDF")

    # Extract the result from the first row and convert to dict
    result = results[0][0]
    try:
        result = json.loads(result)
    except json.JSONDecodeError as e:
        DBOS.logger.error(f"Failed to parse result as JSON: {result}")
        raise ValueError(f"Invalid JSON response from UDF: {str(e)}") from e
    result["_snowflake_query_id"] = query_id
    return result


@v1_router.post("/meetings/jobs", summary="Submit meeting analysis jobs")
async def meetings_jobs(request: MeetingsAnalyzeRequest):
    # TODO: handle deduplication and partitioning based on some request identifier
    result_data = []
    for row in request.data:
        row_index, activity_id, owner_id, salesforce_account_id = row[0], row[1], row[2], row[3]
        handle = await dbos_meetings_jobs_queue.enqueue_async(meetings_durable_workflow, MeetingsJobParams(activity_id=activity_id, owner_id=owner_id, salesforce_account_id=salesforce_account_id))
        workflow_id = handle.get_workflow_id()
        DBOS.logger.info(f"Enqueued post-meeting intelligence workflow. Activity ID: {activity_id}, Workflow ID: {workflow_id}")
        result_data.append(
            [
                row_index,
                {
                    "message": "Successfully enqueued post-meeting intelligence workflow",
                    "workflow_id": workflow_id,
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
    if not is_spcs_environment():
        return True
    session = get_snowflake_session()
    result = session.sql(f"SELECT SALES.RAVEN_DEV.GET_SALES_AI_AUTH_TOKEN('{os.getenv('METAORCHESTRATOR_AUTH_EMAIL')}'):data:access_token::VARCHAR").collect()
    token = result[0][0] if result else None
    if token:
        with open("/sfmnt/sales_ai_metaorchestrator_api_token", "w") as f:
            f.write(token)
        return True
    return False


@DBOS.scheduled("30 */2 * * *")  # crontab syntax to run every 2 hours and 30 minutes (at 30 minutes past every 2nd hour)
@DBOS.workflow()
def rotate_sales_ai_metaorchestrator_api_token(_scheduled_time: datetime, _actual_time: datetime):
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
