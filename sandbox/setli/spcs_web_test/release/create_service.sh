#!/bin/bash -ex

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"

snow spcs service create spcs_web_test \
    --compute-pool sandbox_compute_pool_cpu \
    --spec-path $ROOT/sandbox/setli/spcs_web_test/service_spec.yml \
    --if-not-exists
