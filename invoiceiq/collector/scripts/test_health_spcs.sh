#!/bin/bash

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
SPCS_TOKEN="$($ROOT/invoiceiq/collector/scripts/get_spcs_token.sh)"
SPCS_ENDPOINT="$($ROOT/invoiceiq/collector/scripts/get_spcs_endpoint.sh)"
EMAIL=$(printf %q $(cat $ROOT/invoiceiq/collector/scripts/example_email.eml))
FILE_DIR="$ROOT/invoiceiq/collector/test_files"
URL="https://$SPCS_ENDPOINT/health"

echo "Testing health endpoint at: $URL"
echo "============================================"

echo "Test: Health check"
echo "---------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Snowflake Token=\"$SPCS_TOKEN\"" \
  "$URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

