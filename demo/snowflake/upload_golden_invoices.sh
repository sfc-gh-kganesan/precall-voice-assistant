#!/bin/sh

set -e

root=$(git rev-parse --show-toplevel)
data_path="$root/demo/test_data/snowflake_invoices_golden"
sql="PUT file://$data_path/*.pdf @demo.m1.test_data/snowflake_invoices_golden auto_compress=false;"

./snow.sh ./sql_query.sh "$sql"
