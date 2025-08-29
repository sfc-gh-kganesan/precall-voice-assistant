#!/bin/sh
set -e

echo "Connecting to $SNOWFLAKE_HOST as $SNOWFLAKE_USER..."

# optionally set (output) format argument
[ -n "$2" ] && fmt="$2" || fmt="table"

snow sql -x \
  --host $SNOWFLAKE_HOST \
  --account $SNOWFLAKE_ACCOUNT \
  --user $SNOWFLAKE_USER \
  --mfa-passcode $SNOWFLAKE_OTP \
  --warehouse $SNOWFLAKE_WAREHOUSE \
  --role $SNOWFLAKE_ROLE \
  --enable-templating none \
  --query "$1" \
  --format "$fmt"
