#!/bin/bash -ex

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
REPO=sfengineering-aifde.registry.snowflakecomputing.com/setli/core/image_repository
IMAGE=spcs-web-test
TAG=latest

# Ensure we are logged in to remote registry
snow spcs image-registry login

# Build and push image to repository
docker build --rm --platform linux/amd64 -t $REPO/$IMAGE:$TAG .
docker push $REPO/$IMAGE:$TAG

# Run command to upgrade service to pick up new image
snow spcs service upgrade --spec-path $ROOT/sandbox/setli/spcs_web_test/service_spec.yml

{ set +x; } 2>/dev/null
echo ""
echo "✅ SUCCESS. It may take a minute or two for the service to come back up, please be patient."
