#!/usr/bin/env bash
# Usage:
#   export SNOWFLAKE_PAT="your-pat-token"
#   export SNOWFLAKE_ACCOUNT="your-account-identifier"
#   bash cortex_messages_workaround.sh

set -euo pipefail

: "${SNOWFLAKE_PAT:?Environment variable SNOWFLAKE_PAT is required}"
: "${SNOWFLAKE_ACCOUNT:?Environment variable SNOWFLAKE_ACCOUNT is required}"

curl -sS "https://${SNOWFLAKE_ACCOUNT}.snowflakecomputing.com/api/v2/cortex/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SNOWFLAKE_PAT}" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "[Instructions]Please respond to all questions in Spanish.[/Instructions]"},
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
