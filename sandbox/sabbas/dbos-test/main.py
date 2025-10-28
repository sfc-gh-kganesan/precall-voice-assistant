import time
from datetime import datetime
from typing import Dict, Any
from dbos import DBOS, DBOSConfig
from fastapi import FastAPI
from contextlib import asynccontextmanager

# DBOS Configuration
config: DBOSConfig = {
    "name": "dbos-fastapi-app"
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DBOS on startup"""
    DBOS(config=config)
    DBOS.launch()
    print("✅ DBOS initialized and launched!")
    yield
    print("👋 Shutting down DBOS...")


# Create FastAPI app with DBOS lifespan
app = FastAPI(title="DBOS FastAPI Demo", lifespan=lifespan)


# Simple Hello World endpoint
@app.get("/")
async def hello_world() -> Dict[str, str]:
    """Simple hello world endpoint"""
    return {"message": "Hello World from FastAPI with DBOS!"}


# DBOS Step: Process a task (simulates work)
@DBOS.step()
def process_task(task_id: str, task_data: str) -> Dict[str, str]:
    """A DBOS step that processes a task"""
    print(f"📝 Processing task {task_id}: {task_data}")
    
    # Simulate some long-running processing (5 seconds)
    print(f"⏳ Simulating work for task {task_id}...")
    time.sleep(5)
    
    result = f"Processed: {task_data.upper()}"
    print(f"✅ Completed processing task {task_id}")
    return {
        "task_id": task_id,
        "result": result,
        "status": "completed"
    }


# DBOS Workflow: Queue handler
@DBOS.workflow()
def queue_workflow(task_id: str, task_data: str) -> Dict[str, str]:
    """
    A DBOS workflow that processes queued tasks.
    This is durable - if interrupted, it will resume from the last completed step.
    """
    print(f"🚀 Starting workflow for task {task_id}")
    
    # Step 1: Validate task
    validate_task(task_id, task_data)
    
    # Step 2: Process task
    process_result = process_task(task_id, task_data)
    
    # Step 3: Finalize
    final_result = finalize_task(task_id, process_result)
    
    return final_result


@DBOS.step()
def validate_task(task_id: str, task_data: str) -> Dict[str, bool]:
    """Validate the task"""
    print(f"✓ Validating task {task_id}")
    is_valid = len(task_data) > 0
    return {"task_id": task_id, "valid": is_valid}


@DBOS.step()
def finalize_task(task_id: str, process_result: Dict[str, str]) -> Dict[str, str]:
    """Finalize the task processing"""
    print(f"✓ Finalizing task {task_id}")
    return {
        **process_result,
        "finalized": True,
        "message": "Task completed successfully!"
    }


# Endpoint to enqueue a task
@app.post("/queue/enqueue")
async def enqueue_task(task_id: str, task_data: str) -> Dict[str, str]:
    """
    Enqueue a task for processing.
    This triggers a DBOS workflow that is durable and resilient to failures.
    
    Example:
        POST /queue/enqueue?task_id=123&task_data=hello
    """
    print(f"📨 Received request to enqueue task {task_id}")
    
    # Start the workflow asynchronously
    # DBOS will ensure this completes even if the process crashes
    workflow_handle = DBOS.start_workflow(queue_workflow, task_id, task_data)
    
    return {
        "message": "Task enqueued successfully",
        "task_id": task_id,
        "workflow_id": workflow_handle.workflow_id,
        "status": "enqueued"
    }


# Endpoint to check workflow status
@app.get("/queue/status/{workflow_id}")
async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """
    Check the status of a workflow.
    
    Example:
        GET /queue/status/{workflow_id}
    """
    try:
        handle = DBOS.retrieve_workflow(workflow_id)
        status = handle.get_status()
        
        # Try to get the result if completed
        result = None
        if status.status == "SUCCESS":
            result = handle.get_result()
        
        return {
            "workflow_id": workflow_id,
            "status": status.status,
            "result": result
        }
    except Exception as e:
        return {
            "workflow_id": workflow_id,
            "status": "NOT_FOUND",
            "error": str(e)
        }


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "dbos": "initialized"
    }


# =============================================================================
# SCHEDULED WORKFLOWS EXAMPLE
# =============================================================================

# Simple counter to track executions
execution_count = 0

@DBOS.scheduled('*/30 * * * * *')  # Run every 30 seconds
@DBOS.workflow()
def scheduled_hello(scheduled_time: datetime, actual_time: datetime):
    """
    A simple scheduled workflow that runs every 30 seconds.
    Demonstrates DBOS's scheduled workflow feature.
    """
    global execution_count
    execution_count += 1
    
    DBOS.logger.info(f"👋 Scheduled Hello #{execution_count}")
    DBOS.logger.info(f"   Scheduled: {scheduled_time.strftime('%H:%M:%S')}")
    DBOS.logger.info(f"   Actual: {actual_time.strftime('%H:%M:%S')}")
    
    return {
        "execution": execution_count,
        "scheduled_time": scheduled_time.isoformat(),
        "actual_time": actual_time.isoformat()
    }


# Endpoint to view execution count
@app.get("/scheduled/count")
async def get_scheduled_count() -> Dict[str, Any]:
    """
    View how many times the scheduled workflow has run.
    """
    return {
        "total_executions": execution_count,
        "schedule": "Every 30 seconds",
        "message": "Check server logs to see scheduled workflow executions"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

