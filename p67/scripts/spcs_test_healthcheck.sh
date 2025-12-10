#!/bin/bash

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"/p67
SPCS_ENDPOINT="$("$ROOT/scripts/get_spcs_endpoint_harness.sh")"
URL="$SPCS_ENDPOINT/api/health"

if [ -z "$SNOWFLAKE_PAT" ]; then
    echo "Error: SNOWFLAKE_PAT environment variable is not set." >&2
    exit 1
fi

echo "Testing: $URL"
echo

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Snowflake Token=\"$SNOWFLAKE_PAT\"" \
  "$URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo ">> HTTP Status: $http_code"
echo ">> Response: $response_body"
echo ""

