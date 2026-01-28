#!/bin/bash -ex

# Simple script to call the employees_agent
# Requires SNOW_PAT environment variable to be set with Snowflake Programmatic Access Token

# Configuration
SNOWFLAKE_ACCOUNT_URL="${SNOWFLAKE_ACCOUNT_URL:-https://aifde.snowflakecomputing.com}"
DATABASE="setli"
SCHEMA="sandbox"
AGENT_NAME="employees_agent"

# Check if PAT is set
if [ -z "$SNOW_PAT" ]; then
    echo "Error: SNOW_PAT environment variable is not set"
    exit 1
fi

# Send request to the agent
# Note: if you set the PERSONA variable to 'HR', you can see a subset of the employees (7); changig to 'CEO' will let you see all the employees
curl -v "${SNOWFLAKE_ACCOUNT_URL}/api/v2/databases/${DATABASE}/schemas/${SCHEMA}/agents/${AGENT_NAME}:run" \
    --header 'Content-Type: application/json' \
    --header 'Accept: application/json' \
    --header "Authorization: Bearer ${SNOW_PAT}" \
    --header "X-Snowflake-Authorization-Token-Type: PROGRAMMATIC_ACCESS_TOKEN" \
    --data '{
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "How many employees are there?"
                    }
                ]
            }
        ],
        "variables": {
            "PERSONA": {
                "value": "CEO",
                "type": "string",
                "is_session_variable": true,
                "is_prompt_variable": false
            }
        }
    }'
