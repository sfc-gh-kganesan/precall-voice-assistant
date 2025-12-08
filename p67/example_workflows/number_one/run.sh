#!/bin/bash

echo "Testing Sandboxed JavaScript Execution API"
echo "=========================================="
echo ""

# Check if example file exists
if [ ! -f "dist/index.js" ]; then
  echo "Error: dist/index.js not found!"
  exit 1
fi

# Test execute endpoint
echo "2. Testing /execute endpoint with index.js..."
execute_response=$(curl -s -X POST http://localhost:3000/execute -F "code=@dist/index.js")
echo "Response: $execute_response"
echo ""

echo "=========================================="
echo "Tests completed!"
