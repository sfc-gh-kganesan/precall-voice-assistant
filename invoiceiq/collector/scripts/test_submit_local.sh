#!/bin/bash

# Test script for the /submit endpoint
# Usage: ./test_upload.sh [base_url]

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
EMAIL_CONTENT="$(cat "$ROOT/invoiceiq/collector/scripts/example_email.eml")"
FILE_DIR="$ROOT/invoiceiq/collector/test_files"

randomnum() {
  local min=$1
  local max=$2
  echo $((RANDOM % (max - min + 1) + min))
}

BASE_URL=${1:-"http://127.0.0.1:8000"}
URL="$BASE_URL/submit"

echo "Testing upload endpoint at: $URL"
echo "============================================"

echo "Test: Upload single file"
echo "---------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -F "ticket_number=LIFT-$(randomnum 1 10000)" \
  -F "files=@$FILE_DIR/invoice_01.pdf" \
  --form-string "email=$EMAIL_CONTENT" \
  "$URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

