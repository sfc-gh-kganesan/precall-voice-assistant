#!/bin/bash

################################################################################
# TSW (Troubleshooting Wizard) Integration Test Script
#
# This script tests all 7 TSW diagnostic endpoints using sample data.
#
# Prerequisites:
#   - jq (JSON parser): brew install jq
#   - Service running at http://localhost:8000
#   - Valid API key in .env file
#
# Usage:
#   bash test_tsw_flow.sh [query_id] [case_number] [deployment] [account_id]
#
# Examples:
#   # Use default test values
#   bash test_tsw_flow.sh
#
#   # Provide specific values
#   bash test_tsw_flow.sh 01a6f123-4567-8901-b234-56789abcdef0 00012345 AWS_US_WEST_2 12345
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

# Test data defaults (real data from production database)
# Can be overridden by command line arguments: bash test_tsw_flow.sh <query_id> <case_number> <deployment> <account_id>
#
# To find your own test data, run these SQL queries in Snowflake:
#   Accounts with queries:
#     SELECT DEPLOYMENT, ACCOUNT_ID, COUNT(DISTINCT QUERYID) as query_count, MIN(QUERYID) as sample_query_id
#     FROM DDA_QUERY_METADATA WHERE CLIENT_SEND_TIME > DATEADD('days', -7, CURRENT_DATE)
#     GROUP BY DEPLOYMENT, ACCOUNT_ID HAVING COUNT(*) > 5 ORDER BY query_count DESC LIMIT 5;
#
#   Case numbers with queries:
#     SELECT CASE_NUMBER, COUNT(DISTINCT QUERY_ID) as query_count, MIN(QUERY_ID) as sample_query_id
#     FROM DDA_CASE_QUERYID_MAPPING_V WHERE CASE_NUMBER IS NOT NULL
#     GROUP BY CASE_NUMBER ORDER BY query_count DESC LIMIT 5;
#
QUERY_ID="${1:-01bffaef-0c0c-df7e-0002-f43e51ad64a6}"
CASE_NUMBER="${2:-01087579}"
DEPLOYMENT="${3:-azeastus2prod}"
ACCOUNT_ID="${4:-193598}"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=7

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_step() {
    echo -e "\n${YELLOW}▶ Test $1: $2${NC}"
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

print_warning() {
    echo -e "  ${YELLOW}⚠ $1${NC}"
}

# Generic API call function
call_api() {
    local method=$1
    local endpoint=$2

    curl -s -X "$method" "${BASE_URL}${endpoint}" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Accept: application/json"
}

# Check if response is valid (non-error, non-404, non-500)
is_valid_response() {
    local response=$1

    # Check if response is empty
    if [ -z "$response" ]; then
        return 1
    fi

    # Check if response is "Not Found" (404)
    if echo "$response" | jq -e '.detail == "Not Found"' > /dev/null 2>&1; then
        return 1
    fi

    # Check if response contains "Internal Server Error" (500)
    if echo "$response" | jq -e '.detail' | grep -iq "Internal Server Error" 2>/dev/null; then
        return 1
    fi

    # Check if response contains error detail field
    if echo "$response" | jq -e '.detail' > /dev/null 2>&1; then
        # Has detail field, likely an error (404, 500, etc.)
        return 1
    fi

    return 0
}

# Print preview of API response
print_response_preview() {
    local response=$1
    local max_lines=${2:-3}

    if echo "$response" | jq -e '.' > /dev/null 2>&1; then
        # Valid JSON - pretty print with color
        echo "$response" | jq -C '.' | head -$max_lines
    else
        # Not JSON - print raw
        echo "$response" | head -$max_lines
    fi
}

################################################################################
# Prerequisites Check
################################################################################

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check jq
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}✗ jq is not installed. Install with: brew install jq${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ jq is installed${NC}"

    # Check if service is running
    if ! curl -s --connect-timeout 2 "http://localhost:8000/health" > /dev/null 2>&1; then
        echo -e "${RED}✗ Service is not running at http://localhost:8000${NC}"
        echo "Start the service with: cd dda_service && uv run uvicorn app.main:app --reload"
        exit 1
    fi
    echo -e "${GREEN}✓ Service is running${NC}"
}

################################################################################
# Main Test Flow
################################################################################

run_tests() {
    print_header "TSW Diagnostic Endpoints Integration Tests"

    print_info "Using test data:"
    print_info "  Query ID: $QUERY_ID"
    print_info "  Case Number: $CASE_NUMBER"
    print_info "  Deployment: $DEPLOYMENT"
    print_info "  Account ID: $ACCOUNT_ID"
    echo ""

    # Test 1: UDF Analysis
    print_step "1" "UDF Analysis"
    UDF_RESPONSE=$(call_api "GET" "/tsw/udf/$QUERY_ID")

    if is_valid_response "$UDF_RESPONSE"; then
        print_success "UDF endpoint is working"
        print_info "Response preview:"
        print_response_preview "$UDF_RESPONSE" 5

        # Try to extract some info if available
        if echo "$UDF_RESPONSE" | jq -e '.query_metadata' > /dev/null 2>&1; then
            QUERYID=$(echo "$UDF_RESPONSE" | jq -r '.query_metadata.queryid // "N/A"')
            print_info "Query ID: ${QUERYID:0:20}..."
        fi

        if echo "$UDF_RESPONSE" | jq -e '.udf_analysis' > /dev/null 2>&1; then
            print_info "UDF analysis data present"
        fi
    else
        print_failure "UDF endpoint not working properly"
        ERROR_MSG=$(echo "$UDF_RESPONSE" | jq -r '.detail // "Unknown error"')
        print_info "Error: $ERROR_MSG"
        print_info "Response:"
        print_response_preview "$UDF_RESPONSE" 3
    fi

    # Test 2: Query Compilation Analysis
    print_step "2" "Query Compilation Analysis"
    COMPILATION_RESPONSE=$(call_api "GET" "/tsw/compilation/$CASE_NUMBER")

    if is_valid_response "$COMPILATION_RESPONSE"; then
        print_success "Compilation endpoint is working"

        if echo "$COMPILATION_RESPONSE" | jq -e '.query_metadata' > /dev/null 2>&1; then
            QUERY_COUNT=$(echo "$COMPILATION_RESPONSE" | jq '.query_metadata | length')
            print_info "Found $QUERY_COUNT queries in case"
        fi
    else
        print_failure "Compilation endpoint not working"
        ERROR_MSG=$(echo "$COMPILATION_RESPONSE" | jq -r '.detail // "Unknown error"')
        print_info "Error: $ERROR_MSG"
    fi

    # Test 3: Iceberg Table Diagnostics
    print_step "3" "Iceberg Table Diagnostics"
    ICEBERG_RESPONSE=$(call_api "GET" "/tsw/iceberg/$QUERY_ID?case_number=$CASE_NUMBER")

    if is_valid_response "$ICEBERG_RESPONSE"; then
        print_success "Iceberg endpoint is working"

        if echo "$ICEBERG_RESPONSE" | jq -e '.table_name' > /dev/null 2>&1; then
            TABLE_NAME=$(echo "$ICEBERG_RESPONSE" | jq -r '.table_name // "N/A"')
            print_info "Iceberg table: $TABLE_NAME"
        fi
    else
        print_failure "Iceberg endpoint not working"
        ERROR_MSG=$(echo "$ICEBERG_RESPONSE" | jq -r '.detail // "Unknown error"')
        print_info "Error: $ERROR_MSG"
    fi

    # Test 4: Query Locks Analysis
    print_step "4" "Query Locks Analysis"
    LOCKS_RESPONSE=$(call_api "GET" "/tsw/locks/$DEPLOYMENT/$ACCOUNT_ID/$QUERY_ID?case_number=$CASE_NUMBER")

    if is_valid_response "$LOCKS_RESPONSE"; then
        print_success "Locks endpoint is working"

        if echo "$LOCKS_RESPONSE" | jq -e '.locking_queries' > /dev/null 2>&1; then
            LOCK_COUNT=$(echo "$LOCKS_RESPONSE" | jq '.locking_queries | length')
            print_info "Found $LOCK_COUNT locking queries"
        fi
    else
        print_failure "Locks endpoint not working"
        ERROR_MSG=$(echo "$LOCKS_RESPONSE" | jq -r '.detail // "Unknown error"')
        print_info "Error: $ERROR_MSG"
    fi

    # Test 5: Incident Errors Analysis
    print_step "5" "Incident Errors Analysis"
    INCIDENTS_RESPONSE=$(call_api "GET" "/tsw/incidents/$CASE_NUMBER")

    if is_valid_response "$INCIDENTS_RESPONSE"; then
        print_success "Incidents endpoint is working"

        if echo "$INCIDENTS_RESPONSE" | jq -e '.query_ids' > /dev/null 2>&1; then
            INCIDENT_COUNT=$(echo "$INCIDENTS_RESPONSE" | jq '.query_ids | length')
            print_info "Found $INCIDENT_COUNT queries with incidents"
        fi
    else
        print_failure "Incidents endpoint not working"
        ERROR_MSG=$(echo "$INCIDENTS_RESPONSE" | jq -r '.detail // "Unknown error"')
        print_info "Error: $ERROR_MSG"
    fi

    # Test 6: User Authentication (SAML/OAUTH) Analysis
    print_step "6" "User Authentication (SAML/OAUTH) Analysis"
    AUTH_RESPONSE=$(call_api "GET" "/tsw/auth/$DEPLOYMENT/$ACCOUNT_ID?case_number=$CASE_NUMBER")

    if is_valid_response "$AUTH_RESPONSE"; then
        print_success "Auth endpoint is working"

        if echo "$AUTH_RESPONSE" | jq -e '.saml_integrations' > /dev/null 2>&1; then
            SAML_COUNT=$(echo "$AUTH_RESPONSE" | jq '.saml_integrations | length')
            print_info "Found $SAML_COUNT SAML integrations"
        fi

        if echo "$AUTH_RESPONSE" | jq -e '.oauth_integrations' > /dev/null 2>&1; then
            OAUTH_COUNT=$(echo "$AUTH_RESPONSE" | jq '.oauth_integrations | length')
            print_info "Found $OAUTH_COUNT OAUTH integrations"
        fi
    else
        print_failure "Auth endpoint not working"
        ERROR_MSG=$(echo "$AUTH_RESPONSE" | jq -r '.detail // "Unknown error"')
        print_info "Error: $ERROR_MSG"
    fi

    # Test 7: RBAC Analysis
    print_step "7" "RBAC Analysis"
    RBAC_RESPONSE=$(call_api "GET" "/tsw/rbac/$DEPLOYMENT/$ACCOUNT_ID/$QUERY_ID")

    if is_valid_response "$RBAC_RESPONSE"; then
        print_success "RBAC endpoint is working"

        if echo "$RBAC_RESPONSE" | jq -e '.query_details' > /dev/null 2>&1; then
            ERROR_CODE=$(echo "$RBAC_RESPONSE" | jq -r '.query_details.error_code // "N/A"')
            print_info "Query error code: $ERROR_CODE"
        fi

        if echo "$RBAC_RESPONSE" | jq -e '.candidate_securables' > /dev/null 2>&1; then
            SECURABLE_COUNT=$(echo "$RBAC_RESPONSE" | jq '.candidate_securables | length')
            print_info "Found $SECURABLE_COUNT candidate securables"
        fi
    else
        print_failure "RBAC endpoint not working"
        ERROR_MSG=$(echo "$RBAC_RESPONSE" | jq -r '.detail // "Unknown error"')
        print_info "Error: $ERROR_MSG"
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
        echo -e "\n${GREEN}🎉 All TSW endpoints are working correctly!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Some tests failed - check errors above${NC}"
        echo -e "${YELLOW}Tip: Endpoints may fail if test IDs don't exist in the database${NC}"
        echo -e "${YELLOW}Try running with real query IDs and case numbers${NC}"
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
