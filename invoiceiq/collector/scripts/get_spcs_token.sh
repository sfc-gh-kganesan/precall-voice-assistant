#!/bin/bash -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
SPCS_ENDPOINT="$($ROOT/invoiceiq/collector/scripts/get_spcs_endpoint.sh)"

if [ -z "$SNOWFLAKE_PAT" ]; then
    echo "Error: SNOWFLAKE_PAT environment variable is not set. Hint: you can find this in 1password." >&2
    exit 1
fi

SPCS_TOKEN=$(curl -X POST -s https://SFENGINEERING-AIFDE.snowflakecomputing.com/oauth/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
    -d "subject_token=$SNOWFLAKE_PAT" \
    -d "subject_token_type=programmatic_access_token" \
    -d "scope=session:scope:INVOICEIQ_ADMIN $SPCS_ENDPOINT")

echo $SPCS_TOKEN
