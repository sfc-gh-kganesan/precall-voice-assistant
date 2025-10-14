#!/bin/bash -ex

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"

snow spcs service create -c $INVOICEIQ_SNOW_CONNECT dashboard \
    --compute-pool compute_pool_cpu \
    --spec-path $ROOT/invoiceiq/ui/dashboard/service_spec.yml \
    --if-not-exists

