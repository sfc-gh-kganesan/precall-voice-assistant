#!/usr/bin/env bash
# check-prereqs.sh - Verify all prerequisites for P67 local development
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass=0
fail=0
warn=0

version_gte() {
    # Returns 0 if $1 >= $2 using numeric comparison of major.minor.patch
    local IFS=.
    local -a v1=($1) v2=($2)
    for i in 0 1 2; do
        local a="${v1[$i]:-0}" b="${v2[$i]:-0}"
        if ((a > b)); then return 0; fi
        if ((a < b)); then return 1; fi
    done
    return 0
}

check() {
    local name="$1" cmd="$2" min_version="$3"
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "  ${RED}FAIL${NC}  $name - not found (need $min_version+)"
        ((fail++))
        return
    fi
    local version
    version=$("$cmd" --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)
    if [[ -z "$version" ]]; then
        echo -e "  ${YELLOW}WARN${NC}  $name - found but could not parse version"
        ((warn++))
    elif version_gte "$version" "$min_version"; then
        echo -e "  ${GREEN}OK${NC}    $name $version (need $min_version+)"
        ((pass++))
    else
        echo -e "  ${RED}FAIL${NC}  $name $version is too old (need $min_version+)"
        ((fail++))
    fi
}

echo "P67 Prerequisite Check"
echo "======================"
echo ""

echo "Required tools:"
check "Node.js"        node   "20.0"
check "Bun"            bun    "1.1"
check "pnpm"           pnpm   "10.0"
check "Docker"         docker "20.0"
check "openssl"        openssl "1.0"

echo ""
echo "Docker Compose:"
if docker compose version &>/dev/null; then
    dc_version=$(docker compose version --short 2>/dev/null || docker compose version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    echo -e "  ${GREEN}OK${NC}    Docker Compose $dc_version"
    ((pass++))
else
    echo -e "  ${RED}FAIL${NC}  Docker Compose - not found"
    ((fail++))
fi

echo ""
echo "Docker daemon:"
if docker info &>/dev/null; then
    echo -e "  ${GREEN}OK${NC}    Docker daemon is running"
    ((pass++))
else
    echo -e "  ${RED}FAIL${NC}  Docker daemon is not running - start Docker Desktop"
    ((fail++))
fi

echo ""
echo "Optional tools:"
if command -v snow &>/dev/null; then
    snow_version=$(snow --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    echo -e "  ${GREEN}OK${NC}    Snowflake CLI $snow_version"
    ((pass++))
else
    echo -e "  ${YELLOW}WARN${NC}  Snowflake CLI (snow) - not found (needed for configure.sh)"
    ((warn++))
fi

if command -v jq &>/dev/null; then
    echo -e "  ${GREEN}OK${NC}    jq $(jq --version 2>&1 | grep -oE '[0-9]+\.[0-9.]+' | head -1)"
    ((pass++))
else
    echo -e "  ${YELLOW}WARN${NC}  jq - not found (needed for configure.sh)"
    ((warn++))
fi

echo ""
echo "---"
echo -e "Results: ${GREEN}$pass passed${NC}, ${RED}$fail failed${NC}, ${YELLOW}$warn warnings${NC}"

if ((fail > 0)); then
    echo ""
    echo "Install missing tools before proceeding."
    exit 1
fi
