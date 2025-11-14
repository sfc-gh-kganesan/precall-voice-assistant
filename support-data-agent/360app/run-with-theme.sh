#!/bin/bash

# Helper script to run docker compose with a specific theme
# Usage: ./run-with-theme.sh [theme]
# Available themes: gfinance (default), hackernews, snowflake

THEME=${1:-snowflake}

echo "🎨 Building and running with theme: $THEME"
echo ""

# Export THEME so docker-compose can use it
export THEME=$THEME

# Run docker compose with the theme
docker compose up --build
