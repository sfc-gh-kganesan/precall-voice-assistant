#!/bin/bash

# Test script for the /upload endpoint
# Usage: ./test_upload.sh [base_url]

BASE_URL=${1:-"http://localhost:8000"}
UPLOAD_URL="$BASE_URL/upload"

echo "Testing upload endpoint at: $UPLOAD_URL"
echo "============================================"

# Test 1: Upload single file
echo "Test 2: Upload single file"
echo "---------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -F "ticket_number=INC0789012" \
  -F "files=@test_files/certificate.pdf" \
  -F "files=@test_files/example.pdf" \
  "$UPLOAD_URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""