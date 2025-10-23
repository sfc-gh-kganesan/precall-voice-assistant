# InvoiceIQ LangGraph Workflow

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
| `make test-local` | Send a test request to the local API |
| `make build-spcs` | Build Docker image for SPCS (linux/amd64) |
| `make login-spcs` | Login to Snowflake image registry |
| `make push-spcs` | Push Docker image to SPCS image repository |
| `make clean` | Remove local Docker images |
| `make langgraph-studio` | Startup local LangGraph Studio in browser |


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
make test-local
```

Or use curl directly:
```bash
curl -X POST "http://localhost:8000/process" \
			-H "Content-Type: application/json" \
			-d '{"target_table": "INVOICEIQ.SERVICE.INVOICES", "invoice_id": "2b0771cd-61b4-4ce7-9e29-5bcd9b19a568", "relative_path": "bfb86d4683af4210be180c673c621076_50b88f1f9ebe4317bf3892f66d4c0c74_invoice_01.pdf", "stage_name": "INVOICEIQ.SERVICE.TICKET_ATTACHMENTS"}'
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
make test-local
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

### 5. Test the Service Function

Test the service function with a sample invoice ID:

```sql
SELECT PARSE_JSON(PROCESS_INVOICE(
	'INVOICEIQ.SERVICE.INVOICES',
	'8326c247-3ce0-4116-bb22-a366a587ec87',
	'bfb86d4683af4210be180c673c621076_50b88f1f9ebe4317bf3892f66d4c0c74_invoice_01.pdf',
	'INVOICEIQ.SERVICE.TICKET_ATTACHMENTS' -- Also accepts with '@'
	));
```

Run the service function against table values:
```sql
SELECT 
    PARSE_JSON(invoiceiq.service.PROCESS_INVOICE(
        'invoiceiq.service.INVOICES',
    	INVOICE_ID,
    	RELATIVE_PATH,
    	'INVOICEIQ.SERVICE.TICKET_ATTACHMENTS' -- Also accepts with '@'
	))
FROM invoiceiq.service.INVOICES limit 3;
```

## LangGraph Studio

LangGraph Studio provides interactive visualization to monitor full LangGraph workflow during invocation.

To use LangGraph Studio locally from agent_app root:
```bash
make langraph-studio
```