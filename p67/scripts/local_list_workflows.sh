#!/bin/bash -e

ENDPOINT="http://localhost:3000"
URL="$ENDPOINT/api/workflow/list"

curl -s "$URL"
