#!/bin/bash -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"/p67
ENDPOINT="$("$ROOT/scripts/get_spcs_endpoint_harness.sh")"
URL="$ENDPOINT/api/workflow/create"

if [ -z "$SNOWFLAKE_PAT" ]; then
    echo "Error: SNOWFLAKE_PAT environment variable is not set." >&2
    exit 1
fi

# Check if exactly one argument was provided
if [ $# -ne 1 ]; then
    echo "Error: Exactly one argument required"
    echo "Usage: $0 <filename>"
    exit 1
fi

FILE="$1"

# Check if file exists
if [ ! -f "$FILE" ]; then
    echo "Error: File '$FILE' does not exist"
    exit 1
fi

# Check if file is a zip file
if ! file "$FILE" | grep -q "Zip archive"; then
    echo "Error: File '$FILE' is not a zip file"
    exit 1
fi

# Execute API call
echo "Testing: $URL with $FILE"
echo

curl -X POST "$URL" -F "file=@$1" -H "Authorization: Snowflake Token=\"$SNOWFLAKE_PAT\""
