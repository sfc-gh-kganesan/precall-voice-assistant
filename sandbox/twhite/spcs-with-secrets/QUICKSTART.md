# Quick Start Guide

## Prerequisites

- Docker Desktop running
- Snowflake CLI installed: `pip install snowflake-cli-labs`
- Snowflake connection configured (default connection will be used)

## Automated Test (Recommended)

Run the full end-to-end test:

```bash
./test.sh
```

This will:
1. Setup all Snowflake resources
2. Wait for compute pool to be ready
3. Build and push Docker image
4. Create the service
5. Display logs

## Manual Setup

### 1. Setup Snowflake Resources

Using Snowflake CLI:
```bash
snow sql -f setup.sql
```

Or using justfile:
```bash
just setup
```

### 2. Check Compute Pool Status

```bash
just check-pool
```

Wait until status is ACTIVE or IDLE (2-5 minutes).

### 3. Build and Deploy Image

Using Snowflake CLI:
```bash
# Build image
docker build -t spcs-api-demo:latest .

# Login and push
snow spcs image-registry login
snow spcs image-repository upload \
    --database SPCS_DEMO \
    --schema API_JOBS \
    --repository spcs_demo_repo \
    --image-name spcs-api-demo \
    --tag latest
```

Or using justfile:
```bash
just deploy-cli
```

Or using deploy script:
```bash
./deploy.sh
```

### 4. Create Service

```bash
just create-service
```

### 5. View Logs

```bash
just logs-service
```

## Expected Output

You should see in the logs:
```
Snowflake Container Services - API Demo with Secrets

Configuration:
  API Endpoint: https://api.publicapis.org/entries
  API Key (first 4 chars): demo...
  API Key (full - for demo): demo-api-key-12345-for-testing

Making API request...
  Response Status: 200 OK
API Request Successful
...

Demo Complete
```

## Test Locally (Optional)

```bash
# Set environment variables
export API_KEY="test-key-12345"
export API_ENDPOINT="https://api.publicapis.org/entries"

# Run with Cargo (requires Rust)
cargo run

# Or with Docker
docker build -t spcs-api-demo .
docker run -e API_KEY="test-key" -e API_ENDPOINT="https://api.publicapis.org/entries" spcs-api-demo
```

## Useful Commands

```bash
# Check service status
just status-service

# View logs
just logs-service

# Check compute pool
just check-pool

# List images
just list-images

# Full deployment
just deploy-full

# Cleanup everything
just cleanup
```

Using Snowflake CLI directly:
```bash
# Check services
snow sql -q "SHOW SERVICES IN SCHEMA SPCS_DEMO.API_JOBS;"

# View logs
snow spcs service logs api_job_service --container-name api-client

# List secrets
snow sql -q "SHOW SECRETS IN SCHEMA SPCS_DEMO.API_JOBS;"

# List network rules
snow sql -q "SHOW NETWORK RULES IN SCHEMA SPCS_DEMO.API_JOBS;"
```

## Cleanup

```bash
# Using justfile
just cleanup

# Or using SQL file
snow sql -f cleanup.sql
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Compute pool stuck in STARTING | Wait 2-5 minutes, this is normal |
| Image push fails | Check Docker login, verify registry URL |
| Service creation fails | Verify compute pool is ACTIVE/IDLE |
| No logs visible | Wait 30-60 seconds after service creation |
| Network access denied | Verify network rule includes the API host |

## What This Demo Shows

- Secrets Management: API key stored securely in Snowflake secret
- Network Rules: Controlled egress to specific external APIs
- External Access Integration: Links network rules to services
- Container Services: Rust app running in SPCS
- Environment Variables: Secrets injected at runtime
- Snowflake CLI: Modern deployment workflow
- Best Practices: No hardcoded credentials, audit trail, least privilege

For detailed information, see [README.md](README.md)

