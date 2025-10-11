#!/bin/bash -ex

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
REPO=sfengineering-aifde.registry.snowflakecomputing.com/invoiceiq/service/image_repository
IMAGE=invoiceiq-collector
TAG=latest

# Ensure we are logged in to remote registry
snow spcs image-registry login $INVOICEIQ_SNOW_CONNECT

# Build and push image to repository
docker build --rm --platform linux/amd64 -t $REPO/$IMAGE:$TAG .
docker push $REPO/$IMAGE:$TAG

# Run command to upgrade service to pick up new image
snow spcs service upgrade $INVOICEIQ_SNOW_CONNECT collector --spec-path $ROOT/invoiceiq/collector/service_spec.yml

{ set +x; } 2>/dev/null
echo ""
echo "✅ SUCCESS. It may take a minute or two for the service to come back up, please be patient."
