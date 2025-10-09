## To run FastAPI app locally:

Ensure required env vars are captured in .env
```
SNOWFLAKE_ACCOUNT=<account-identifier>
SNOWFLAKE_USER=<snowflake-username>
SNOWFLAKE_PAT=<SNOWFLAKE_PAT>
```

```bash
# From agent_app directory
uv run python -m app.main
```

Send a test message
```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{"ticket_number": "xyz"}'
```

## To run FastAPI in local Docker container

Build Docker image
```bash
cd agent_app
docker build -t invoiceiq-agent:latest .
```

Ensure required env vars are captured in .env
```
SNOWFLAKE_ACCOUNT=<account-identifier>
SNOWFLAKE_USER=<snowflake-username>
SNOWFLAKE_PAT=<SNOWFLAKE_PAT>
```

Run Docker container with environment file
```bash
docker run --rm --env-file .env -p 8000:8000 invoiceiq-agent:latest
```

Send a test message
```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{"ticket_number": "xyz"}'
```

## To run as Service Function in SPCS

Build the image
```bash
cd agent_app
docker build --rm --platform linux/amd64 -t sfengineering-aifde.registry.snowflakecomputing.com/invoiceiq/service/image_repository/invoiceiq-agent:latest .
```

Login to Snowflake image registry
```bash
snow spcs image-registry login -c "<connection-name>" 
```

Upload the docker image to Snowflake image repository
```bash
docker push sfengineering-aifde.registry.snowflakecomputing.com/invoiceiq/service/image_repository/invoiceiq-agent:latest
```