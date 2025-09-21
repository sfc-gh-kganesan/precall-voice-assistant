#!/bin/bash

# Test script for the /upload endpoint
# Usage: ./test_upload.sh [base_url]

BASE_URL=${1:-"http://localhost:8000"}
UPLOAD_URL="$BASE_URL/upload"

echo "Testing upload endpoint at: $UPLOAD_URL"
echo "============================================"

# Test 1: Upload multiple files with a ticket number
echo "Test 1: Upload multiple files"
echo "------------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -F "ticket_number=INC0123456" \
  -F "files=@test_files/invoice1.txt" \
  -F "files=@test_files/invoice2.txt" \
  -F "files=@test_files/receipt.pdf" \
  "$UPLOAD_URL")

# Extract HTTP code and response body
http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

# Test 2: Upload single file
echo "Test 2: Upload single file"
echo "---------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -F "ticket_number=INC0789012" \
  -F "files=@test_files/invoice1.txt" \
  "$UPLOAD_URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

# Test 3: Test validation error (missing ticket number)
echo "Test 3: Missing ticket number (should fail)"
echo "--------------------------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -F "files=@test_files/invoice1.txt" \
  "$UPLOAD_URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

# Test 4: Test validation error (missing files)
echo "Test 4: Missing files (should fail)"
echo "------------------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -F "ticket_number=INC0345678" \
  "$UPLOAD_URL")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

# Test 5: Check health endpoint
echo "Test 5: Health check"
echo "---------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/health")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $http_code"
echo "Response: $response_body"
echo ""

echo "============================================"
echo "Testing complete!"
echo ""
echo "To start the server: make dev"
echo "To run this script: ./test_upload.sh"