#!/bin/bash

set -e

snow spcs service logs $INVOICEIQ_SNOW_CONNECT invoiceiq.service.collector --container-name collector --instance-id 0

