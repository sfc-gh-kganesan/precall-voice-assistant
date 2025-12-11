#!/bin/bash -e

if [ -z "$SNOWFLAKE_PAT" ]; then
    echo "Error: SNOWFLAKE_PAT environment variable is not set." >&2
    exit 1
fi

# Check if exactly one argument was provided
if [ $# -ne 1 ]; then
    echo "Error: Exactly one argument required"
    echo "Usage: $0 <workflow id>"
    exit 1
fi

wfid="$1"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"/p67
ENDPOINT="$("$ROOT/scripts/get_spcs_endpoint_harness.sh")"
URL="$ENDPOINT/api/workflow/${wfid}/run"

# Execute API call
echo "Testing: $URL"
echo

curl -X POST "$URL" -H "Authorization: Snowflake Token=\"$SNOWFLAKE_PAT\""
