#!/bin/bash -e

snow spcs service list-endpoints p67.app.harness --format json | jq '.[] | select(.name == "app") | .ingress_url' -r | xargs -I {} echo "https://{}"
