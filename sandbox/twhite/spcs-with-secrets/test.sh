#!/bin/bash
# End-to-end test script using Snowflake CLI

set -e

echo "SPCS Demo - End-to-End Test"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v snow &> /dev/null; then
    echo "Error: Snowflake CLI not found. Install with: pip install snowflake-cli-labs"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "Prerequisites OK"
echo ""

# Step 1: Setup Snowflake resources
echo "Step 1: Setting up Snowflake resources..."
snow sql -f setup.sql

echo ""
echo "Step 2: Waiting for compute pool to be ready..."
echo "This may take 2-5 minutes..."

# Wait for compute pool to be ACTIVE or IDLE
MAX_WAIT=300
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    STATUS=$(snow sql -q "SHOW COMPUTE POOLS;" --format json | grep -o '"state":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "UNKNOWN")
    
    if [ "$STATUS" = "ACTIVE" ] || [ "$STATUS" = "IDLE" ]; then
        echo "Compute pool is $STATUS"
        break
    fi
    
    echo "Compute pool status: $STATUS (waited ${WAITED}s)"
    sleep 10
    WAITED=$((WAITED + 10))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "Warning: Compute pool not ready after ${MAX_WAIT}s. You may need to wait longer."
    echo "Check status with: snow sql -q 'SHOW COMPUTE POOLS;'"
fi

echo ""
echo "Step 3: Building Docker image..."
docker build -t spcs-api-demo:latest .

echo ""
echo "Step 4: Logging into Snowflake registry..."
snow spcs image-registry login

echo ""
echo "Step 5: Uploading image to Snowflake..."
snow spcs image-repository upload \
    --database SPCS_DEMO \
    --schema API_JOBS \
    --repository spcs_demo_repo \
    --image-name spcs-api-demo \
    --tag latest

echo ""
echo "Step 6: Verifying image..."
snow spcs image-repository list-images \
    --database SPCS_DEMO \
    --schema API_JOBS \
    --repository spcs_demo_repo

echo ""
echo "Step 7: Creating service..."
snow sql -q "
USE DATABASE SPCS_DEMO;
USE SCHEMA API_JOBS;

CREATE OR REPLACE SERVICE api_job_service
  IN COMPUTE POOL job_pool
  FROM SPECIFICATION \$\$
spec:
  containers:
  - name: api-client
    image: /spcs_demo/api_jobs/spcs_demo_repo/spcs-api-demo:latest
    env:
      API_KEY:
        secretKeyRef:
          key: api_key_secret
      API_ENDPOINT: 'https://api.publicapis.org/entries'
  externalAccessIntegrations:
  - api_access_integration
\$\$
MIN_INSTANCES = 1
MAX_INSTANCES = 1;
"

echo ""
echo "Step 8: Waiting for service to start..."
sleep 15

echo ""
echo "Step 9: Checking service status..."
snow sql -q "SHOW SERVICES IN SCHEMA SPCS_DEMO.API_JOBS;"

echo ""
echo "Step 10: Fetching service logs..."
snow spcs service logs api_job_service --container-name api-client || echo "Service may still be starting..."

echo ""
echo "Test Complete!"
echo ""
echo "To view logs again, run:"
echo "  just logs-service"
echo ""
echo "To clean up, run:"
echo "  snow sql -f cleanup.sql"

