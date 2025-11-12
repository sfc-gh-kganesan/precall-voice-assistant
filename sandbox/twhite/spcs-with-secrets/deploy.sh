#!/bin/bash
# Deployment script for SPCS using Snowflake CLI

set -e

echo "Snowflake Container Services Deployment"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if Snowflake CLI is installed
if ! command -v snow &> /dev/null; then
    echo "Error: Snowflake CLI not found. Install with: pip install snowflake-cli-labs"
    exit 1
fi

echo "Building Docker image..."
docker build -t spcs-api-demo:latest .

echo ""
echo "Pushing image to Snowflake using CLI..."
snow spcs image-registry login

# Upload image to repository
# Format: /database/schema/repository/image:tag
snow spcs image-repository upload \
    --database SPCS_DEMO \
    --schema API_JOBS \
    --repository spcs_demo_repo \
    --image-name spcs-api-demo \
    --tag latest

echo ""
echo "Verifying image upload..."
snow spcs image-repository list-images \
    --database SPCS_DEMO \
    --schema API_JOBS \
    --repository spcs_demo_repo

echo ""
echo "Deployment Complete"
echo ""
echo "Next steps:"
echo "1. Check compute pool status:"
echo "   snow sql -q 'SHOW COMPUTE POOLS;'"
echo ""
echo "2. Create the service (if compute pool is ACTIVE/IDLE):"
echo "   snow sql -f setup.sql"
echo ""
echo "3. Monitor the service:"
echo "   snow spcs service logs api_job_service --container-name api-client"

