#!/bin/sh -e

# Important: this script assumes that you have already successfully run
# `make golden_purchase_orders` from the //demo/test_data directory.
#
# This script creates and populates two tables using sample data:
#   - invoiceiq.service.purchase_order
#   - invoiceiq.service.purchase_order_line_item
#
check_file() {
    local filepath="$1"

    if [ ! -f "$filepath" ]; then
        echo "❌ $filepath does not exist"
        return 1
    fi
}

root=$(git rev-parse --show-toplevel)
test_data_dir="$root/demo/test_data"
po_header_file="$test_data_dir/golden_purchase_orders/purchase_order_header_data.csv"
po_line_items_file="$test_data_dir/golden_purchase_orders/purchase_order_line_items.csv"

if check_file "$po_header_file" && check_file "$po_line_items_file"; then
    echo "Initializing data tables..."
else
    echo "\nPlease run: make golden_purchase_orders -C $test_data_dir"
    echo "See $test_data_dir/README.md for full instructions"
    exit 1
fi

sql_header=$(python3 $root/demo/scripts/csv_to_snowflake.py --table-name invoiceiq.service.purchase_order $po_header_file)
sql_line_items=$(python3 $root/demo/scripts/csv_to_snowflake.py --table-name invoiceiq.service.purchase_order_line_item $po_line_items_file)

snow sql --silent --enable-templating none -q "$sql_header" $INVOICEIQ_SNOW_CONNECT
snow sql --silent --enable-templating none -q "$sql_line_items" $INVOICEIQ_SNOW_CONNECT

echo "✅ SUCCESS"
