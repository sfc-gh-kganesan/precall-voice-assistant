# DBOS FastAPI Queue Example

A simple FastAPI application integrated with DBOS to demonstrate durable workflow execution and queue processing.

## Features

- ✅ FastAPI Hello World endpoint
- 🔄 DBOS durable workflows
- 📨 Queue-based task processing
- 💪 Resilient to failures (workflows auto-resume)
- 📊 Workflow status tracking

## Installation

```bash
# Install dependencies
uv sync
```

## Running the Application

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the FastAPI server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`

## API Endpoints

### 1. Hello World
```bash
curl http://localhost:8000/
```

Response:
```json
{
  "message": "Hello World from FastAPI with DBOS!"
}
```

### 2. Enqueue a Task
```bash
curl -X POST "http://localhost:8000/queue/enqueue?task_id=task-123&task_data=process_this_data"
```

Response:
```json
{
  "message": "Task enqueued successfully",
  "task_id": "task-123",
  "workflow_id": "wf_abc123...",
  "status": "enqueued"
}
```

### 3. Check Workflow Status
```bash
curl http://localhost:8000/queue/status/{workflow_id}
```

Response:
```json
{
  "workflow_id": "wf_abc123...",
  "status": "SUCCESS",
  "result": {
    "task_id": "task-123",
    "result": "Processed: PROCESS_THIS_DATA",
    "status": "completed",
    "finalized": true,
    "message": "Task completed successfully!"
  }
}
```

### 4. Health Check
```bash
curl http://localhost:8000/health
```

### 5. View Scheduled Workflow Count
```bash
curl http://localhost:8000/scheduled/count
```

Response:
```json
{
  "total_executions": 5,
  "schedule": "Every 30 seconds",
  "message": "Check server logs to see scheduled workflow executions"
}
```

## DBOS Features Demonstrated

### 1. Durable Workflows
The `queue_workflow` function is decorated with `@DBOS.workflow()`, making it durable:
- If the application crashes mid-execution, the workflow automatically resumes from the last completed step
- Workflow state is persisted in the DBOS system database

### 2. Steps
Individual steps within a workflow are decorated with `@DBOS.step()`:
- Each step's completion is recorded
- Steps are idempotent and won't re-execute on workflow resume

### 3. Workflow Management
- Start workflows asynchronously with `DBOS.start_workflow()`
- Retrieve workflow status with `DBOS.retrieve_workflow()`
- Check results and status of completed workflows

### 4. Scheduled Workflows
The `scheduled_hello` workflow demonstrates automatic periodic execution:
- Runs every 30 seconds using `@DBOS.scheduled('*/30 * * * * *')`
- Executes automatically in the background
- Takes exactly two arguments: `scheduled_time` and `actual_time` (both `datetime` objects)
- Runs exactly once per interval (guaranteed by DBOS's idempotency)
- Uses crontab syntax for scheduling (with seconds as the first field)

## Database Configuration

By default, DBOS uses SQLite (no configuration needed).

For production with PostgreSQL:
```bash
export DBOS_SYSTEM_DATABASE_URL="postgresql://user:password@host:port/database"
```

## Interactive Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Example Usage Flow

```bash
# 1. Start the server
python main.py

# 2. Enqueue a task
WORKFLOW_ID=$(curl -s -X POST "http://localhost:8000/queue/enqueue?task_id=test-1&task_data=hello_world" | jq -r '.workflow_id')

# 3. Check status
curl http://localhost:8000/queue/status/$WORKFLOW_ID

# 4. See the result
curl http://localhost:8000/queue/status/$WORKFLOW_ID | jq '.result'
```

## What Makes This Special?

Unlike traditional task queues (like Celery, RQ, etc.), DBOS workflows are **durable by default**:

1. **Automatic Recovery**: If your application crashes, workflows automatically resume when you restart
2. **No Lost Tasks**: All workflow state is persisted in the database
3. **Idempotent Steps**: Steps won't re-execute on resume, saving time and preventing duplicate operations
4. **Simple Code**: No need for complex retry logic or state management
5. **Built-in Scheduling**: Scheduled workflows run exactly once per interval with guaranteed idempotency

Try it: Start a long-running task, kill the server mid-execution, restart it, and watch the workflow continue from where it left off!

## Observing Scheduled Workflows

After starting the server, watch the logs to see the scheduled workflow run every 30 seconds:

```
👋 Scheduled Hello #1
   Scheduled: 10:30:00
   Actual: 10:30:00
👋 Scheduled Hello #2
   Scheduled: 10:30:30
   Actual: 10:30:30
```

Or check the count via API:
```bash
# Keep checking to see the count increase
watch -n 5 "curl -s http://localhost:8000/scheduled/count | jq"
```

