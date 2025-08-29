#!/bin/sh

set -e

sf="$(git rev-parse --show-toplevel)/demo/snowflake"
$sf/helpers/snow.sh $sf/helpers/sql_query.sh "select * from demo.m1.invoices" csv > $1
