#!/bin/sh

set -e

sf="$(git rev-parse --show-toplevel)/demo/snowflake"
$sf/helpers/snow.sh $sf/helpers/sql_file.sh $sf/sql/init_account.sql
