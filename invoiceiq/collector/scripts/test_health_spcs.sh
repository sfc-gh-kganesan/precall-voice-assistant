#!/bin/bash

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
SPCS_ENDPOINT="$($ROOT/invoiceiq/collector/scripts/get_spcs_endpoint.sh)"
EMAIL=$(printf %q $(cat $ROOT/invoiceiq/collector/scripts/example_email.eml))
FILE_DIR="$ROOT/invoiceiq/collector/test_files"
URL="https://$SPCS_ENDPOINT/health"

if [ -z "$SNOWFLAKE_PAT" ]; then
    echo "Error: SNOWFLAKE_PAT environment variable is not set. Hint: you can find this in 1password." >&2
    exit 1
fi

echo "Testing health endpoint at: $URL"
echo "============================================"

echo "Test: Health check"
echo "---------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Snowflake Token=\"$SNOWFLAKE_PAT\"" \
  "$URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

