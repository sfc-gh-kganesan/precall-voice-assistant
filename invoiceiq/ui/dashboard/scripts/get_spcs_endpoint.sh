#!/bin/bash

# Get the ingress URL for the dashboard service
INGRESS_URL=$(snow spcs service list-endpoints dashboard -c "$INVOICEIQ_SNOW_CONNECT" --format json 2>/dev/null | grep -o '"ingress_url": "[^"]*"' | cut -d'"' -f4 | head -n1)

if [ -z "$INGRESS_URL" ]; then
    echo "⚠️  Could not extract ingress URL. Showing full endpoint info:"
    snow spcs service list-endpoints dashboard -c "$INVOICEIQ_SNOW_CONNECT"
else
    echo "Dashboard URL: https://$INGRESS_URL"
fi

