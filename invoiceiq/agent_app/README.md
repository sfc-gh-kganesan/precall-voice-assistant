# InvoiceIQ Agent App

An AI-powered invoice processing agent built with FastAPI and LangGraph. This service analyzes invoices and makes intelligent decisions about invoice processing using Snowflake Cortex.

## Prerequisites

Before running this application, ensure that:
- The Snowflake database and tables have been initialized by running the SQL scripts in `invoiceiq/snowflake/`
- You have access to a Snowflake account with appropriate permissions
- Recommended: You have a Snowflake Personal Access Token (PAT)

## Makefile Commands

The following commands are available via `make`:

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make run` | Run the FastAPI app locally with uv |
| `make build-local` | Build Docker image for local use |
| `make run-local` | Run Docker container locally (requires .env file) |
| `make test` | Send a test request to the local API |
| `make build-spcs` | Build Docker image for SPCS (linux/amd64) |
| `make login-spcs` | Login to Snowflake image registry |
| `make push-spcs` | Push Docker image to SPCS image repository |
| `make clean` | Remove local Docker images |

## Running Locally

### 1. Configure Environment Variables

Create a `.env` file based on the provided `.env.example`:

```bash
cp env.example .env
```

Edit `.env` and fill in your Snowflake credentials:
```
SNOWFLAKE_ACCOUNT=<account-identifier>
SNOWFLAKE_USER=<snowflake-username>
SNOWFLAKE_PAT=<your-personal-access-token>
```

### 2. Run the Application

```bash
make run
```

### 3. Test the API

Send a test request to the running service:
```bash
make test
```

Or use curl directly:
```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{"invoice_id": "74f1cb0b-07ba-4a6f-8c71-4c0dc212b90e"}'
```

## Running in Docker

### 1. Configure Environment Variables

Ensure your `.env` file is configured (see "Running Locally" section above).

### 2. Build the Docker Image

```bash
make build-local
```

### 3. Run the Container

```bash
make run-local
```

### 4. Test the API

```bash
make test
```

## Running in Snowpark Container Services (SPCS)

### 1. Build the SPCS-Compatible Image

```bash
make build-spcs
```

### 2. Login to Snowflake Image Registry

```bash
make login-spcs CONNECTION_NAME=<your-connection-name>
```

Replace `<your-connection-name>` with your Snowflake CLI connection name.

### 3. Push the Image to Snowflake

```bash
make push-spcs
```

### 4. Create the Service and Functions

Execute the SQL commands in `agent_app/snowflake/service.sql` to create:
- The SPCS service
- The `PROCESS_INVOICE` service function
- The tasks for automated invoice processing

### 5. Test the Service Function

Test the service function with a sample invoice ID:

```sql
SELECT PARSE_JSON(PROCESS_INVOICE('8326c247-3ce0-4116-bb22-a366a587ec87'));
```

### 6. Execute Tasks

To process invoices manually, execute the tasks:

```sql
-- Execute the task that consumes from the stream
EXECUTE TASK consume_invoices_stream_task;

-- Execute the task that processes and cleans up invoices
EXECUTE TASK process_and_cleanup_invoice_task;
```

To enable automated processing, resume the tasks:

```sql
ALTER TASK consume_invoices_stream_task RESUME;
ALTER TASK process_and_cleanup_invoice_task RESUME;
```

## API Endpoints

- `POST /process` - Process an invoice by invoice_id
- `GET /healthcheck` - Health check endpoint for service readiness

## LangGraph Studio

LangGraph Studio provides interactive visualization to monitor full LangGraph workflow during invocation.

To use LangGraph Studio locally from agent_app root:
```bash
make langraph-studio
```