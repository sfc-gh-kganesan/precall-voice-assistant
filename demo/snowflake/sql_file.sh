#!/bin/sh
set -e

echo "Connecting to $SNOWFLAKE_HOST as $SNOWFLAKE_USER..."

snow sql -x \
  --host $SNOWFLAKE_HOST \
  --account $SNOWFLAKE_ACCOUNT \
  --user $SNOWFLAKE_USER \
  --mfa-passcode $SNOWFLAKE_OTP \
  --warehouse demowh \
  --filename $1
