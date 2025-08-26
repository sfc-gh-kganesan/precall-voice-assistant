#!/bin/sh
set -e

# Load secrets from 1password to environment variables, as defined in snow.env
op run --no-masking --env-file="./snow.env" -- "$@"

