#!/bin/bash -e

snow spcs service list-endpoints $INVOICEIQ_SNOW_CONNECT collector --format json | jq '.[] | select(.name == "collector") | .ingress_url' -r
