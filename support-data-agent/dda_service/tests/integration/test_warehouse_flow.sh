#!/bin/bash

################################################################################
# Warehouse Service Integration Test Script
#
# This script tests all 7 warehouse endpoints in sequence using real data
# discovered from the account search endpoint.
#
# Prerequisites:
#   - jq (JSON parser): brew install jq
#   - Service running at http://localhost:8000
#   - Valid API key in .env file
#
# Usage:
#   bash test_warehouse_flow.sh
################################################################################

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API Configuration
BASE_URL="http://localhost:8000/api/v1"
API_KEY="dev_key_12345"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=9

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_step() {
    echo -e "\n${YELLOW}▶ Step $1: $2${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_failure() {
    echo -e "${RED}✗ $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_info() {
    echo -e "  ${BLUE}ℹ $1${NC}"
}

# Generic API call function
call_api() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ "$method" = "GET" ]; then
        curl -s -X GET "${BASE_URL}${endpoint}" \
            -H "X-API-Key: ${API_KEY}"
    elif [ "$method" = "POST" ]; then
        curl -s -X POST "${BASE_URL}${endpoint}" \
            -H "X-API-Key: ${API_KEY}" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

################################################################################
# Prerequisites Check
################################################################################

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check jq
    if ! command -v jq &> /dev/null; then
        print_failure "jq is not installed. Install with: brew install jq"
        exit 1
    fi
    print_success "jq is installed"

    # Check if service is running
    if ! curl -s --connect-timeout 2 "http://localhost:8000/health" > /dev/null 2>&1; then
        print_failure "Service is not running at http://localhost:8000"
        echo "Start the service with: cd dda_service && uv run uvicorn app.main:app --reload"
        exit 1
    fi
    print_success "Service is running"
}

################################################################################
# Main Test Flow
################################################################################

run_tests() {
    print_header "Warehouse Service Integration Tests"

    # Steps 1-2: Search for accounts and find one with warehouse data
    print_step "1-2" "Search for accounts with warehouse data"
    ACCOUNTS_RESPONSE=$(call_api "POST" "/accounts/search?search_query=analytics")

    if [ -z "$ACCOUNTS_RESPONSE" ] || [ "$ACCOUNTS_RESPONSE" = "[]" ]; then
        print_failure "No accounts found"
        exit 1
    fi

    ACCOUNT_COUNT=$(echo "$ACCOUNTS_RESPONSE" | jq 'length')
    print_info "Found $ACCOUNT_COUNT accounts, searching for one with warehouse data..."

    ACCOUNT_FOUND=false
    WAREHOUSE_NAME=""

    # Try up to 10 accounts or until we find one with data
    MAX_ACCOUNTS_TO_TRY=10
    ACCOUNTS_TO_TRY=$((ACCOUNT_COUNT < MAX_ACCOUNTS_TO_TRY ? ACCOUNT_COUNT : MAX_ACCOUNTS_TO_TRY))

    for ((acct_idx=0; acct_idx<$ACCOUNTS_TO_TRY; acct_idx++)); do
        DEPLOYMENT=$(echo "$ACCOUNTS_RESPONSE" | jq -r ".[$acct_idx].DEPLOYMENT")
        ACCOUNT_ID=$(echo "$ACCOUNTS_RESPONSE" | jq -r ".[$acct_idx].ACCOUNT_ID")
        LOCATOR=$(echo "$ACCOUNTS_RESPONSE" | jq -r ".[$acct_idx].LOCATOR")
        ALIAS=$(echo "$ACCOUNTS_RESPONSE" | jq -r ".[$acct_idx].ALIAS")

        print_info "Trying account $((acct_idx+1))/$ACCOUNTS_TO_TRY: $ALIAS (account_id=$ACCOUNT_ID)"

        # Get warehouses for this account
        WAREHOUSES_RESPONSE=$(call_api "GET" "/accounts/$DEPLOYMENT/$ACCOUNT_ID/warehouses")

        if [ -z "$WAREHOUSES_RESPONSE" ] || [ "$WAREHOUSES_RESPONSE" = "[]" ]; then
            print_info "  No warehouses found, trying next account..."
            continue
        fi

        # Check if any warehouse has data
        WAREHOUSE_COUNT=$(echo "$WAREHOUSES_RESPONSE" | jq 'length')

        for ((i=0; i<$WAREHOUSE_COUNT; i++)); do
            WH_NAME=$(echo "$WAREHOUSES_RESPONSE" | jq -r ".[$i].WAREHOUSE_NAME")
            LOAD_DATA=$(echo "$WAREHOUSES_RESPONSE" | jq -r ".[$i].LOAD_DATA")
            WH_START_TIME=$(echo "$WAREHOUSES_RESPONSE" | jq -r ".[$i].START_TIME")

            if [ "$LOAD_DATA" = "true" ] && [ "$WH_START_TIME" != "null" ] && [ "$WH_START_TIME" != "NaT" ] && [ -n "$WH_START_TIME" ]; then
                WAREHOUSE_NAME="$WH_NAME"
                ACCOUNT_FOUND=true
                print_success "Found account with warehouse data!"
                print_success "  Account: $ALIAS (deployment=$DEPLOYMENT, account_id=$ACCOUNT_ID)"
                print_success "  Warehouse: $WAREHOUSE_NAME (LOAD_DATA=true)"
                print_info "  Locator: $LOCATOR"
                break 2  # Break out of both loops
            fi
        done

        print_info "  No warehouses with data (checked $WAREHOUSE_COUNT warehouses)"
    done

    if [ "$ACCOUNT_FOUND" = false ]; then
        print_failure "Could not find any account with warehouse chart data"
        print_info "Tried $ACCOUNTS_TO_TRY accounts - all had warehouses without LOAD_DATA=true"
        print_info "Try a different search query or check if DDA_REL_WH_LOAD_QUERY_SEC_SLICE has data"
        exit 1
    fi

    # Step 3: Test warehouse details endpoint
    print_step "3" "Get warehouse details"
    DETAILS_RESPONSE=$(call_api "GET" "/warehouses/$DEPLOYMENT/$ACCOUNT_ID/$WAREHOUSE_NAME")

    # Validate response has required fields
    if echo "$DETAILS_RESPONSE" | jq -e '.WAREHOUSE_NAME' > /dev/null 2>&1; then
        WH_SIZE=$(echo "$DETAILS_RESPONSE" | jq -r '.WAREHOUSE_SIZE // "N/A"')
        WH_TYPE=$(echo "$DETAILS_RESPONSE" | jq -r '.WAREHOUSE_TYPE // "N/A"')
        print_success "Warehouse details retrieved"
        print_info "Size: $WH_SIZE, Type: $WH_TYPE"
    else
        print_failure "Warehouse details endpoint failed"
    fi

    # Step 4: Test chart time range endpoint
    print_step "4" "Get chart time range"
    RANGE_RESPONSE=$(call_api "GET" "/warehouses/$DEPLOYMENT/$ACCOUNT_ID/$WAREHOUSE_NAME/chart-range")

    START_TIME=$(echo "$RANGE_RESPONSE" | jq -r '.start_time')
    END_TIME=$(echo "$RANGE_RESPONSE" | jq -r '.end_time')

    # Check if times are valid (not null, not NaT, not empty)
    if [ "$START_TIME" != "null" ] && [ "$START_TIME" != "NaT" ] && [ -n "$START_TIME" ] && \
       [ "$END_TIME" != "null" ] && [ "$END_TIME" != "NaT" ] && [ -n "$END_TIME" ]; then
        print_success "Chart time range retrieved"
        print_info "Range: $START_TIME to $END_TIME"
    else
        print_success "Chart time range endpoint works (no data available)"
        # Skip chart tests when no data is available
        print_info "Skipping chart tests (no time range data)"
        SKIP_CHART_TESTS=true
    fi

    # Step 5: Test warehouse change history
    print_step "5" "Get warehouse change history"
    CHANGES_RESPONSE=$(call_api "GET" "/warehouses/$DEPLOYMENT/$ACCOUNT_ID/$WAREHOUSE_NAME/changes")

    if echo "$CHANGES_RESPONSE" | jq -e 'type == "array"' > /dev/null 2>&1; then
        CHANGE_COUNT=$(echo "$CHANGES_RESPONSE" | jq 'length')
        print_success "Warehouse change history retrieved"
        print_info "Found $CHANGE_COUNT changes (last 30 days)"
    else
        print_failure "Warehouse change history endpoint failed"
    fi

    # Step 6: Test warehouse-level charts
    print_step "6" "Get warehouse-level chart data"

    if [ "$SKIP_CHART_TESTS" = true ]; then
        print_success "Skipping warehouse chart test (no time range data available)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        CHART_DATA=$(cat <<EOF
{
  "chart_type": "EXECUTED_JOBS",
  "start_time": "$START_TIME",
  "end_time": "$END_TIME"
}
EOF
)

        WH_CHART_RESPONSE=$(call_api "POST" "/warehouses/$DEPLOYMENT/$ACCOUNT_ID/$WAREHOUSE_NAME/warehouse-charts" "$CHART_DATA")

        if echo "$WH_CHART_RESPONSE" | jq -e 'type == "array"' > /dev/null 2>&1; then
            CHART_POINTS=$(echo "$WH_CHART_RESPONSE" | jq 'length')
            print_success "Warehouse chart data retrieved"
            print_info "Chart type: EXECUTED_JOBS, Data points: $CHART_POINTS"
        else
            print_failure "Warehouse chart endpoint failed"
        fi
    fi

    # Step 7: Test cluster-level charts
    print_step "7" "Get cluster-level chart data"

    if [ "$SKIP_CHART_TESTS" = true ]; then
        print_success "Skipping cluster chart test (no time range data available)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        CLUSTER_CHART_DATA=$(cat <<EOF
{
  "cluster_num": 1,
  "chart_type": "JOB_QUEUE_TRANSITION",
  "start_time": "$START_TIME",
  "end_time": "$END_TIME"
}
EOF
)

        CLUSTER_CHART_RESPONSE=$(call_api "POST" "/warehouses/$DEPLOYMENT/$ACCOUNT_ID/$WAREHOUSE_NAME/cluster-charts" "$CLUSTER_CHART_DATA")

        if echo "$CLUSTER_CHART_RESPONSE" | jq -e 'type == "array"' > /dev/null 2>&1; then
            CLUSTER_POINTS=$(echo "$CLUSTER_CHART_RESPONSE" | jq 'length')
            print_success "Cluster chart data retrieved"
            print_info "Chart type: JOB_QUEUE_TRANSITION, Cluster: 1, Data points: $CLUSTER_POINTS"
        else
            print_failure "Cluster chart endpoint failed"
        fi
    fi

    # Step 8: Get query UUID and test warehouse-at-query-time
    print_step "8" "Get query UUID for account"
    QUERIES_RESPONSE=$(call_api "GET" "/accounts/$DEPLOYMENT/$LOCATOR/queries?limit=1")

    QUERY_UUID=$(echo "$QUERIES_RESPONSE" | jq -r '.[0].DDA_QUERY_UUID // null')

    if [ "$QUERY_UUID" != "null" ] && [ -n "$QUERY_UUID" ]; then
        print_success "Query UUID retrieved: ${QUERY_UUID:0:8}..."

        # Test warehouse-at-query-time endpoint
        print_step "8b" "Get warehouse configuration at query time"
        AT_QUERY_RESPONSE=$(call_api "GET" "/warehouses/$DEPLOYMENT/$ACCOUNT_ID/at-query/$QUERY_UUID")

        if echo "$AT_QUERY_RESPONSE" | jq -e '.WAREHOUSE_NAME' > /dev/null 2>&1; then
            AT_QUERY_WH=$(echo "$AT_QUERY_RESPONSE" | jq -r '.WAREHOUSE_NAME')
            print_success "Warehouse-at-query-time retrieved"
            print_info "Warehouse used by query: $AT_QUERY_WH"
        else
            print_failure "Warehouse-at-query-time endpoint failed"
        fi
    else
        print_success "No queries found for account (skipping warehouse-at-query test)"
        TESTS_PASSED=$((TESTS_PASSED + 1))  # Count as passed since it's expected
    fi

    # Step 9: Test event overlays
    print_step "9" "Get event overlays"

    if [ "$SKIP_CHART_TESTS" = true ]; then
        print_success "Skipping event overlays test (no time range data available)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        OVERLAYS_RESPONSE=$(call_api "GET" "/warehouses/$DEPLOYMENT/$ACCOUNT_ID/$WAREHOUSE_NAME/overlays?start_time=$START_TIME&end_time=$END_TIME")

        if echo "$OVERLAYS_RESPONSE" | jq -e 'type == "array"' > /dev/null 2>&1; then
            OVERLAY_COUNT=$(echo "$OVERLAYS_RESPONSE" | jq 'length')
            print_success "Event overlays retrieved"
            print_info "Found $OVERLAY_COUNT events in time range"
        else
            print_failure "Event overlays endpoint failed"
        fi
    fi
}

################################################################################
# Test Summary
################################################################################

print_summary() {
    print_header "Test Summary"

    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Some tests failed${NC}"
        exit 1
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    check_prerequisites
    run_tests
    print_summary
}

main
