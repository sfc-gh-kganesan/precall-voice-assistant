#!/bin/sh
set -e


sf="$(git rev-parse --show-toplevel)/demo/snowflake"

# Load secrets from 1password to environment variables, as defined in snow.env
op run --no-masking --env-file="$sf/snow.env" -- "$@"

