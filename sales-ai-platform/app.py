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

from evals.langsmith_evals import evaluate_use_case_summary_prod, lookup_eval_scores_from_snowflake
from evals.prod_logging import build_eval_transcript_lookup_query
from graphs.post_meeting_workflow import graph as post_meeting_graph
from utils import _rotate_token_impl, compute_eval_id, execute_graph_in_stream, execute_snowflake_query_sync, get_sales_ai_metaorchestrator_api_token

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
CURRENT_GRAPH_VERSION = os.getenv("GRAPH_VERSION", "1.1.1")


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
            },
            config={"graph_version": CURRENT_GRAPH_VERSION},
        )
        return [row_index, MeetingsAnalyzeResponse(analysis=result)]

    tasks = [process_row(row[0], row[1], row[2], row[3]) for row in request.data]
    response = await asyncio.gather(*tasks)
    return {"data": response}


# ============================================================================
# Meeting Evals RPC
# ============================================================================


class EvalScores(BaseModel):
    """Model for the evaluation scores."""

    accuracy: float = Field(description="The accuracy score")
    groundedness: float = Field(description="The groundedness score")
    completeness: float = Field(description="The completeness score")
    actionability: float = Field(description="The actionability score")


class MeetingsEvalsResponse(BaseModel):
    """Response model for the meeting evals."""

    eval_id: str = Field(description="The evaluation ID, computed from the activity_id, owner_id, salesforce_account_id, and graph_version")
    salesforce_account_id: str = Field(description="The Salesforce account ID of the call")
    owner_id: str = Field(description="The owner ID of the call")
    activity_id: str = Field(description="The activity ID of the call")
    graph_version: str = Field(description="The model version used for the evaluation")
    scores: EvalScores = Field(description="The evaluation scores of the meeting")
    eval_success: bool = Field(description="Whether the evaluation was successful")
    eval_error_message: str = Field(description="The error message from the evaluation")
    error_stage: str = Field(description="The stage of the evaluation that failed")


@v1_router.post("/meetings/evals/", summary="Evaluate new use cases generated from a meeting transcript")
async def meetings_evals(request: MeetingsAnalyzeRequest):
    """
    Evaluate the new use cases generated from a meeting transcript.
    """

    async def process_row(row_index: int, activity_id: str, owner_id: str, salesforce_account_id: str, graph_version: str):
        eval_id = compute_eval_id(activity_id, owner_id, salesforce_account_id, graph_version)
        existing = await lookup_eval_scores_from_snowflake(eval_id)

        if existing:
            eval_response = MeetingsEvalsResponse(
                eval_id=eval_id,
                salesforce_account_id=salesforce_account_id,
                owner_id=owner_id,
                activity_id=activity_id,
                graph_version=graph_version,
                scores=EvalScores(
                    accuracy=existing["eval_result"]["accuracy"],
                    groundedness=existing["eval_result"]["groundedness"],
                    completeness=existing["eval_result"]["completeness"],
                    actionability=existing["eval_result"]["actionability"],
                ),
                eval_success=existing["eval_state"]["eval_success"],
                eval_error_message=existing["eval_state"]["eval_error_message"],
                error_stage=existing["eval_state"]["error_stage"],
            )
            return [row_index, eval_response]

        # Execute the graph in a stream to get the intermediate states
        result = await execute_graph_in_stream(app.state.post_meeting_graph, activity_id, owner_id, salesforce_account_id)
        transcript = result["extract_transcript"]["call_transcript"]

        # Evaluate the graph output
        eval_results = await evaluate_use_case_summary_prod(salesforce_account_id, owner_id, activity_id, graph_version, transcript, result["new_use_case_assistant"]["new_use_cases"])
        eval_scores = eval_results["scores"] if eval_results else None

        # Compose the evaluation response
        eval_response = MeetingsEvalsResponse(
            eval_id=eval_results["eval_id"] if eval_results else "N/A",
            salesforce_account_id=salesforce_account_id,
            owner_id=owner_id,
            activity_id=activity_id,
            graph_version=graph_version,
            scores=EvalScores(
                accuracy=eval_scores["accuracy"] if eval_scores else 0.0,
                groundedness=eval_scores["groundedness"] if eval_scores else 0.0,
                completeness=eval_scores["completeness"] if eval_scores else 0.0,
                actionability=eval_scores["actionability"] if eval_scores else 0.0,
            ),
            eval_success=eval_results["eval_success"],
            eval_error_message=eval_results["eval_error_message"],
            error_stage=eval_results["error_stage"],
        )
        return [row_index, eval_response]

    tasks = [process_row(row[0], row[1], row[2], row[3], CURRENT_GRAPH_VERSION) for row in request.data]
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

    # Build the query to invoke the TRIGGER_SALES_AI_WORKFLOW UDF
    langgraph_query = f"""
    SELECT SALES.RAVEN_DEV.TRIGGER_SALES_AI_WORKFLOW(
        '{auth_token}',
        PARSE_JSON('{payload_json}')
    )
    """
    graph_results, query_id = None, None
    try:
        # Execute query in thread pool to avoid blocking event loop
        # This will block for ~2 minutes, but in a separate thread
        DBOS.logger.info(f"Executing Snowflake query for activity_id: {args.activity_id}")
        graph_results, query_id = await asyncio.to_thread(execute_snowflake_query_sync, langgraph_query)
        DBOS.logger.info(f"Snowflake query completed with query_id: {query_id}")

    except Exception as e:
        DBOS.logger.error(f"Snowflake query failed: {str(e)}")
        raise ValueError(f"Failed to execute TRIGGER_SALES_AI_WORKFLOW UDF: {str(e)}") from e

    # Validate results and extract the result from the first row and convert to dict
    if not graph_results:
        raise ValueError("No results returned from TRIGGER_SALES_AI_WORKFLOW UDF")

    # Extract the result from the first row and convert to dict
    result = graph_results[0][0]
    try:
        result = json.loads(result)
    except json.JSONDecodeError as e:
        DBOS.logger.error(f"Failed to parse result as JSON: {result}")
        raise ValueError(f"Invalid JSON response from UDF: {str(e)}") from e
    result["_snowflake_query_id"] = query_id

    # Run evals for the new use cases generation
    call_transcript_lookup_query = build_eval_transcript_lookup_query(args.owner_id, args.activity_id, args.salesforce_account_id)
    call_transcript = None
    try:
        call_transcript = await asyncio.to_thread(execute_snowflake_query_sync, call_transcript_lookup_query)
        call_transcript = {k.lower(): v for k, v in call_transcript[0][0].as_dict().items()} if call_transcript else None
    except Exception as e:
        DBOS.logger.error(f"Failed to lookup call transcript for activity_id: {args.activity_id}: {str(e)}")
        raise ValueError(f"Failed to lookup call transcript: {str(e)}") from e

    eval_results = None
    try:
        temporary_results = await app.state.post_meeting_graph.ainvoke(
            {
                "activity_id": args.activity_id,
                "owner_id": args.owner_id,
                "salesforce_account_id": args.salesforce_account_id,
            },
            config={"graph_version": CURRENT_GRAPH_VERSION},
        )
        eval_results = await evaluate_use_case_summary_prod(args.salesforce_account_id, args.owner_id, args.activity_id, CURRENT_GRAPH_VERSION, call_transcript["raw_content"], temporary_results["new_use_cases"])
    except Exception as e:
        DBOS.logger.error(f"Failed to evaluate use case summary for activity_id: {args.activity_id}: {str(e)}")
        raise ValueError(f"Failed to evaluate use case summary: {str(e)}") from e
    result["eval_id"] = eval_results["eval_id"] if eval_results else "N/A"
    result["eval_scores"] = eval_results["scores"] if eval_results else None
    result["eval_success"] = eval_results["eval_success"] if eval_results else None
    result["eval_error_message"] = eval_results["eval_error_message"] if eval_results else None
    result["error_stage"] = eval_results["error_stage"] if eval_results else None
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
