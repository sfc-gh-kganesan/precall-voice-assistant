#!/bin/bash

# Test script for the /upload endpoint
# Usage: ./test_upload.sh [base_url]
#

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
EMAIL=$(printf %q $(cat $ROOT/invoiceiq/collector/scripts/example_email.eml))

randomnum() {
  local min=$1
  local max=$2
  echo $((RANDOM % (max - min + 1) + min))
}

BASE_URL=${1:-"http://localhost:8000"}
UPLOAD_URL="$BASE_URL/submit"

echo "Testing upload endpoint at: $UPLOAD_URL"
echo "============================================"

echo "Test: Upload single file"
echo "---------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -F "ticket_number=LIFT-$(randomnum 1 10000)" \
  -F "files=@test_files/invoice_01.pdf" \
  -F "email=\"$EMAIL\"" \
  "$UPLOAD_URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

