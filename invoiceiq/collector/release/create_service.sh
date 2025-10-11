#!/bin/bash -ex

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"

snow spcs service create $INVOICEIQ_SNOW_CONNECT collector \
    --compute-pool compute_pool_cpu \
    --spec-path $ROOT/invoiceiq/collector/service_spec.yml \
    --if-not-exists
