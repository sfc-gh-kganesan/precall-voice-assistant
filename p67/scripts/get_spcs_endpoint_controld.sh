#!/bin/bash -e

snow spcs service list-endpoints p67.app.controld --format json | jq '.[] | select(.name == "web") | .ingress_url' -r | xargs -I {} echo "https://{}"
