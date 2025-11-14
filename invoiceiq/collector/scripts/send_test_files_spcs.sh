#!/bin/bash

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
SPCS_ENDPOINT="$($ROOT/invoiceiq/collector/scripts/get_spcs_endpoint.sh)"
EMAIL_CONTENT="$(cat "$ROOT/invoiceiq/collector/scripts/example_email.eml")"
ZIP_DIR="$ROOT/invoiceiq/collector/samples"
LIMIT=${1:-}  # Pass a number to limit files processed, default is no limit

if [ -z "$SNOWFLAKE_PAT" ]; then
    echo "Error: SNOWFLAKE_PAT environment variable is not set. Hint: you can find this in 1password." >&2
    exit 1
fi

randomnum() {
  local min=$1
  local max=$2
  echo $((RANDOM % (max - min + 1) + min))
}

URL="https://$SPCS_ENDPOINT/submit"

echo "Testing submit endpoint: $URL"
echo "============================================"

# Create a temporary directory for extraction
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Unzip all zip files in the samples directory
echo "Extracting files from $ZIP_DIR..."
for zipfile in "$ZIP_DIR"/*.zip; do
  if [ -f "$zipfile" ]; then
    unzip -q "$zipfile" -d "$TEMP_DIR"
  fi
done

# Count PDF files (excluding macOS metadata files)
pdf_count=$(find "$TEMP_DIR" -type f -name "*.pdf" -not -path "*/__MACOSX/*" -not -name "._*" | wc -l)
echo "Found $pdf_count PDF files to upload"
echo "============================================"
echo ""

# Loop through all PDF files and send them
counter=1

# Build find pipeline with optional limit (excluding macOS metadata files)
if [ -n "$LIMIT" ]; then
  file_stream=$(find "$TEMP_DIR" -type f -name "*.pdf" -not -path "*/__MACOSX/*" -not -name "._*" | head -n $LIMIT)
else
  file_stream=$(find "$TEMP_DIR" -type f -name "*.pdf" -not -path "*/__MACOSX/*" -not -name "._*")
fi

while IFS= read -r file; do
  if [ -f "$file" ]; then
    ticket_num="LIFT-$(randomnum 1 10000)"
  
    echo "[$counter/$pdf_count] Uploading: $file"
    echo "Ticket Number: $ticket_num"
    echo "---------------------------"

    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
      -F "ticket_number=$ticket_num" \
      -F "files=@$file" \
      --form-string "email=$EMAIL_CONTENT" \
      -F "snowflake_database=${SNOWFLAKE_DATABASE:-}" \
      -F "snowflake_schema=${SNOWFLAKE_SCHEMA:-}" \
      -F "snowflake_stage=${SNOWFLAKE_STAGE:-}" \
      -F "snowflake_warehouse=${SNOWFLAKE_WAREHOUSE:-}" \
      -F "snowflake_role=${SNOWFLAKE_ROLE:-}" \
      -F "snowflake_account=${SNOWFLAKE_ACCOUNT:-}" \
      -F "snowflake_user=${SNOWFLAKE_USER:-}" \
      -H "Authorization: Snowflake Token=\"${SNOWFLAKE_PAT}\"" \
      "$URL")

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    response_body=$(echo "$response" | grep -v "HTTP_CODE:")

    echo "HTTP Status: $http_code"
    echo "Response: $response_body"
    echo ""
    
    counter=$((counter + 1))
    
    # Wait 5 seconds between requests
    sleep 5
  fi
done <<< "$file_stream"

echo "============================================"
echo "Batch upload complete!"