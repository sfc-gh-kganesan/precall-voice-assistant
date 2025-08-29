#!/bin/sh

set -e

# Important: this script assumes that you have already successfully run 
# `make golden_invoices` from the //demo/test_data directory.
#
# Here we uploading the pdfs from //demo/test_data/golden_invoices to a snowflake stage
demo="$(git rev-parse --show-toplevel)/demo"
data_path="$demo/test_data/golden_invoices"

sql="PUT file://$data_path/*.pdf @demo.m1.test_data/golden_invoices auto_compress=false;"
$demo/snowflake/helpers/snow.sh ./$demo/snowflake/helpers/sql_query.sh "$sql"
