#!/bin/bash -e

# Check if exactly one argument was provided
if [ $# -ne 1 ]; then
    echo "Error: Exactly one argument required"
    echo "Usage: $0 <workflow id>"
    exit 1
fi

wfid="$1"
ENDPOINT="http://localhost:3000"
URL="$ENDPOINT/api/workflow/${wfid}/run"

# Execute API call
echo "Testing: $URL"
echo

curl -X POST "$URL"
