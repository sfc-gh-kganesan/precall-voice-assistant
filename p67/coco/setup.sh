#!/bin/bash -ex

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"/p67/coco

# Prepare custom commands
mkdir -p ~/.snowflake/cortex/commands
ln -sf $ROOT/commands/define-workflow.md ~/.snowflake/cortex/commands/p67-define-workflow.md
ln -sf $ROOT/commands/generate-workflow.md ~/.snowflake/cortex/commands/p67-generate-workflow.md
ln -sf $ROOT/commands/p67 ~/.snowflake/cortex/commands/p67

# Prepare demo directory
base_dir="demo"
dir_name="$base_dir"
counter=1

# Check if directory exists and find the next available name
while [ -d "$dir_name" ]; do
    dir_name="${base_dir}-${counter}"
    ((counter++))
done

# Create the directory
mkdir "$dir_name"

cp ./assets/cortex_search_usage.yaml "$dir_name"
cp ./assets/AGENTS.md "$dir_name"

# Launch CoCo
cd "$dir_name"

# Get default SnowCLI connection name if not SNOW_CONNECTION is unset
default_connection=${SNOW_CONNECTION:=$(snow connection list --format json | jq -r '.[] | select(.is_default == true) | .connection_name')}

snow connection list
read -p "Which SNOW CLI connection do you want to use? (default: $default_connection) >> " snow_connection
snow_connection=${snow_connection:-$default_connection}
cortex -c $snow_connection
