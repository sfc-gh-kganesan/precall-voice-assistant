#!/bin/bash -ex

ENV_FILE=$ROOT/ops/.env

if [ ! -f $ENV_FILE ]; then
    { set +x; } 2>/dev/null
    echo ""
    echo ".env file does not exist: $ENV_FILE"
    echo "Please run: 'make .env -C $ROOT/release' and then customize the values as needed."
    return 1
fi

# Assign environment variables defined in .env
export $(cat $ENV_FILE|xargs)

# Get default SnowCLI connection name if not SNOW_CONNECTION is unset
SNOW_CONNECTION=${SNOW_CONNECTION:=$(snow connection list --format json | jq -r '.[] | select(.is_default == true) | .connection_name')}


