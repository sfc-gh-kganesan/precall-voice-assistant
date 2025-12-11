#!/bin/bash -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"/p67
ENDPOINT="$("$ROOT/scripts/get_spcs_endpoint_harness.sh")"
URL="$ENDPOINT/api/workflow/list"

if [ -z "$SNOWFLAKE_PAT" ]; then
    echo "Error: SNOWFLAKE_PAT environment variable is not set." >&2
    exit 1
fi

curl -s "$URL" -H "Authorization: Snowflake Token=\"$SNOWFLAKE_PAT\""
