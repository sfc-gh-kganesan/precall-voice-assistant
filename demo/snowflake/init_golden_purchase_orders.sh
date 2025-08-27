#!/bin/sh

set -e

# Important: this script assumes that you have already successfully run 
# `make golden_purchase_orders` from the //demo/test_data directory.
#
# Here we are using the csv_to_snowflake.py script to convert a csv file to
# a series of SQL statements that will create a table and populate it with
# the rows from the csv.
root=$(git rev-parse --show-toplevel)
data_path="$root/demo/test_data/golden_purchase_orders/purchase_orders.csv"
sql=$(python $root/demo/scripts/csv_to_snowflake.py --table-name demo.m1.purchase_orders $data_path)
./snow.sh ./sql_query.sh "$sql"
