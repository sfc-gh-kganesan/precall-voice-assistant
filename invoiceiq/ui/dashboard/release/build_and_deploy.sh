#!/bin/bash -ex

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
REPO=sfengineering-aifde.registry.snowflakecomputing.com/invoiceiq/service/image_repository
IMAGE=invoiceiq-dashboard
TAG=latest

echo "🔧 Building InvoiceIQ Dashboard with Express proxy server"

# Ensure we are logged in to remote registry
snow spcs image-registry login -c $INVOICEIQ_SNOW_CONNECT

# Change to dashboard directory where Dockerfile is located
cd $ROOT/invoiceiq/ui/dashboard

# Build and push image to repository
docker build --rm --platform linux/amd64 -t $REPO/$IMAGE:$TAG .
docker push $REPO/$IMAGE:$TAG

# Run command to upgrade service to pick up new image
snow spcs service upgrade -c $INVOICEIQ_SNOW_CONNECT dashboard --spec-path $ROOT/invoiceiq/ui/dashboard/service_spec.yml

{ set +x; } 2>/dev/null
echo ""
echo "✅ SUCCESS. It may take a minute or two for the service to come back up, please be patient."

