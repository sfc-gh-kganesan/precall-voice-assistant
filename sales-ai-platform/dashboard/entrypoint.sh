#!/bin/bash
set -euo pipefail # Good practice: Exit immediately if any command fails

echo "Starting Streamlit application..."

# Use 'exec' to ensure Streamlit becomes the main container process (PID 1).
# This prevents the container from immediately exiting after successful launch.
exec streamlit run dashboard.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
