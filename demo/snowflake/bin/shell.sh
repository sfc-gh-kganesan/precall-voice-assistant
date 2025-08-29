#!/bin/sh

set -e

sf="$(git rev-parse --show-toplevel)/demo/snowflake"
$sf/helpers/snow.sh $sf/helpers/connect_shell.sh
