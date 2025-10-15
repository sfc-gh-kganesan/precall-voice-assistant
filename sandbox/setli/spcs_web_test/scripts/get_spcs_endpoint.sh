#!/bin/bash -e

snow spcs service list-endpoints spcs_web_test --format json | jq '.[] | select(.name == "web") | .ingress_url' -r
