#!/bin/bash

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
SPCS_ENDPOINT="$($ROOT/invoiceiq/collector/scripts/get_spcs_endpoint.sh)"
EMAIL=$(printf %q $(cat $ROOT/invoiceiq/collector/scripts/example_email.eml))
FILE_DIR="$ROOT/invoiceiq/collector/test_files"

if [ -z "$SNOWFLAKE_PAT" ]; then
    echo "Error: SNOWFLAKE_PAT environment variable is not set. Hint: you can find this in 1password." >&2
    exit 1
fi

randomnum() {
  local min=$1
  local max=$2
  echo $((RANDOM % (max - min + 1) + min))
}

URL="https://$SPCS_ENDPOINT/submit"

echo "Testing submit endpoint: $URL"
echo "============================================"

echo "Test: Upload single file"
echo "---------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -F "ticket_number=LIFT-$(randomnum 1 10000)" \
  -F "files=@$FILE_DIR/invoice_01.pdf" \
  -F "email=\"$EMAIL\"" \
  -H "Authorization: Snowflake Token=\"$SNOWFLAKE_PAT\"" \
  "$URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

