#!/bin/bash
#
# Theme Switcher for Docker Compose
#
# Usage: ./set-theme.sh gfinance
#        ./set-theme.sh hackernews
#        ./set-theme.sh snowflake

THEME=${1:-gfinance}

echo "🎨 Setting theme to: $THEME"
echo "THEME=$THEME" > .env.theme

echo "✅ Theme set! Now run:"
echo "   docker compose up --build"
