# InvoiceIQ Backend API

Backend API for InvoiceIQ - provides endpoints for invoice management and status updates.

## Development

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Setup

1. Install dependencies:

   ```bash
   make install
   ```

2. Create a `.env` file with required environment variables:

   ```bash
   # Snowflake Configuration
   SNOWFLAKE_ACCOUNT=SFENGINEERING-AIFDE
   SNOWFLAKE_USER=svc_invoiceiq
   SNOWFLAKE_PAT=your_personal_access_token
   SNOWFLAKE_WAREHOUSE=compute_wh
   SNOWFLAKE_DATABASE=invoiceiq
   SNOWFLAKE_SCHEMA=service
   SNOWFLAKE_ROLE=invoiceiq_admin
   
   # Agent Service URL (langgraph_workflow service)
   # Local dev: http://localhost:8000
   # SPCS: invoice-processing-service.<compute-pool>.svc.spcs.internal:8000
   AGENT_SERVICE_URL=http://localhost:8000
   ```

   **Note:** For local development, start the agent with `cd ../langgraph_workflow && make run`

3. Run the development server:
   ```bash
   make dev
   ```

   The API will be available at `http://localhost:8001`

### Code Quality

Format code:
```bash
make format
```

Lint code:
```bash
make lint
```

Type check:
```bash
make typecheck
```

### Docker Development

Run in Docker container:

```bash
docker build -t invoiceiq-backend .
docker run -p 8001:8001 -v $(pwd)/app:/app/app invoiceiq-backend
```

## Build and deploy to SPCS

### Prerequisites

* [`docker`](https://docs.docker.com/engine/install/) container engine
* [`snow`](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) CLI tool installed and configured with a default connection setup to the Snowflake account where the service will be deployed (sfengineering-aifde). If you want to use a non-default connection with the `snow` command, please export the `INVOICEIQ_SNOW_CONNECT` environment variable. For example, to use the connection `invoiceiq`, you would export `INVOICEIQ_SNOW_CONNECT="-c invoiceiq"`.

### Build and Deploy

This script will build the image with docker, push it to the remote repository, and restart the SPCS service to pick up the new image:

```bash
./release/build_and_deploy.sh
```

### Create Service (First Time Only)

To create the SPCS service for the first time:

```bash
./release/create_service.sh
```

### Helper Scripts

Get service status and endpoint:
```bash
./scripts/get_spcs_endpoint.sh
```

View service logs:
```bash
./scripts/get_spcs_logs.sh
```

Delete the service:
```bash
./release/drop_service.sh
```

## API Documentation

When running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### Main Endpoints

- `GET /invoices` - List invoices with filtering
- `PATCH /invoices/status` - Update invoice status
- `GET /invoices/{invoice_id}/download` - Download invoice file
- `GET /health` - Health check endpoint

