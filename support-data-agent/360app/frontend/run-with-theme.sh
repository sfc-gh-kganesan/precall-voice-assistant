#!/bin/bash
#
# Build and run with specific theme
#
# Usage: ./run-with-theme.sh gfinance
#        ./run-with-theme.sh hackernews
#        ./run-with-theme.sh snowflake

THEME=${1:-gfinance}

echo "🎨 Building and running with theme: $THEME"
THEME=$THEME docker compose up --build
