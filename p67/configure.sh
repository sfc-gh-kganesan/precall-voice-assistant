#!/bin/bash

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get default SnowCLI connection name if not SNOW_CONNECTION is unset
default_connection=${SNOW_CONNECTION:=$(snow connection list --format json | jq -r '.[] | select(.is_default == true) | .connection_name')}

# Prompt user for input
snow connection list
read -p "Which SNOW CLI connection do you want to use? (default: $default_connection) >> " snow_connection
snow_connection=${snow_connection:-$default_connection}

# Paths to the files
makefile="$root/Makefile"

# Copy files
cp $makefile.template $makefile

# Replace placeholders in Makefile file using | as delimiter
sed -i "" "s|<<snow_connection>>|$snow_connection|g" $makefile

echo "$makefile is ready to use. `make -C $root`"
