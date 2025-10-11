#!/bin/bash

# Test script for the /health endpoint
# Usage: ./test_health_local.sh [base_url]

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
EMAIL=$(printf %q $(cat $ROOT/invoiceiq/collector/scripts/example_email.eml))
FILE_DIR="$ROOT/invoiceiq/collector/test_files"

randomnum() {
  local min=$1
  local max=$2
  echo $((RANDOM % (max - min + 1) + min))
}

BASE_URL=${1:-"http://localhost:8000"}
URL="$BASE_URL/health"

echo "Testing health endpoint at: $URL"
echo "============================================"

echo "Test: Health check"
echo "---------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  "$URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

