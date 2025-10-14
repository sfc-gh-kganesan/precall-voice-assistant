#!/bin/bash

# Get the ingress URL for the backend service
INGRESS_URL=$(snow spcs service list-endpoints backend -c "$INVOICEIQ_SNOW_CONNECT" --format json 2>/dev/null | grep -o '"ingress_url": "[^"]*"' | cut -d'"' -f4 | head -n1)

if [ -z "$INGRESS_URL" ]; then
    echo "⚠️  Could not extract ingress URL. Showing full endpoint info:"
    snow spcs service list-endpoints backend -c "$INVOICEIQ_SNOW_CONNECT"
else
    echo "Backend Endpoint: https://$INGRESS_URL"
fi

