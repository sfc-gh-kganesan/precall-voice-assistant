#!/usr/bin/env bash
# doctor.sh - Diagnose the state of a P67 local development environment
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Resolve p67 root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
P67_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

pass=0
fail=0
warn=0

ok()   { echo -e "  ${GREEN}OK${NC}    $1"; ((pass++)); }
bad()  { echo -e "  ${RED}FAIL${NC}  $1"; ((fail++)); }
note() { echo -e "  ${YELLOW}WARN${NC}  $1"; ((warn++)); }
section() { echo ""; echo -e "${CYAN}[$1]${NC}"; }

section "Prerequisites"
for cmd in node bun pnpm docker openssl; do
    if command -v "$cmd" &>/dev/null; then
        ok "$cmd found"
    else
        bad "$cmd not found"
    fi
done
if docker compose version &>/dev/null; then ok "docker compose available"; else bad "docker compose not available"; fi

section "Docker Daemon"
if docker info &>/dev/null; then
    ok "Docker daemon running"
else
    bad "Docker daemon not running"
fi

section "Port Availability"
for port in 5432 3002; do
    if lsof -i :"$port" -sTCP:LISTEN &>/dev/null; then
        pid=$(lsof -ti :"$port" -sTCP:LISTEN 2>/dev/null | head -1)
        proc=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        # Docker-managed ports are expected
        if [[ "$proc" == *"docker"* ]] || [[ "$proc" == *"com.docker"* ]]; then
            ok "Port $port in use by Docker (expected)"
        else
            note "Port $port in use by $proc (PID $pid)"
        fi
    else
        ok "Port $port is free"
    fi
done

section "Configuration Files"
if [[ -f "$P67_ROOT/Makefile" ]]; then
    ok "Root Makefile exists (configure.sh was run)"
else
    bad "Root Makefile missing - run ./configure.sh"
fi

for envfile in "$P67_ROOT/packages/db/.env" "$P67_ROOT/services/controld/.env"; do
    rel="${envfile#$P67_ROOT/}"
    if [[ -f "$envfile" ]]; then
        ok "$rel exists"
    else
        note "$rel missing - will be created by 'make dev'"
    fi
done

if [[ -f "$P67_ROOT/.env" ]]; then
    if grep -q '^ENCRYPTION_KEY=.' "$P67_ROOT/.env" 2>/dev/null; then
        ok "ENCRYPTION_KEY is set in .env"
    else
        note "ENCRYPTION_KEY is empty in .env - 'make dev' will generate it"
    fi
else
    note "Root .env missing - 'make dev' will handle this"
fi

section "Docker Containers"
if docker info &>/dev/null; then
    cd "$P67_ROOT"
    for svc in postgres controld; do
        status=$(docker compose ps --format json 2>/dev/null | grep -o "\"$svc\"" &>/dev/null && \
                 docker compose ps --status running --format '{{.Name}}' 2>/dev/null | grep "$svc" || true)
        if [[ -n "$status" ]]; then
            ok "$svc container is running"
        else
            note "$svc container is not running"
        fi
    done
else
    note "Skipping container checks (Docker not running)"
fi

section "Database"
if docker info &>/dev/null && docker compose -f "$P67_ROOT/compose.yaml" ps --status running --format '{{.Name}}' 2>/dev/null | grep -q postgres; then
    if docker compose -f "$P67_ROOT/compose.yaml" exec -T postgres pg_isready -U postgres &>/dev/null; then
        ok "PostgreSQL is accepting connections"
    else
        bad "PostgreSQL container running but not accepting connections"
    fi
    # Check if migrations have been applied
    table_count=$(docker compose -f "$P67_ROOT/compose.yaml" exec -T postgres psql -U postgres -d controld_dev -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo "0")
    if [[ "$table_count" -gt 0 ]]; then
        ok "Database has $table_count tables (migrations applied)"
    else
        note "Database appears empty - migrations may not have run"
    fi
else
    note "Skipping database checks (postgres not running)"
fi

section "CLI"
if command -v p67 &>/dev/null; then
    ok "p67 CLI is in PATH ($(which p67))"
else
    bad "p67 CLI not found in PATH"
fi

if [[ -f "$P67_ROOT/tools/p67-cli/bin/p67" ]]; then
    ok "CLI binary exists at tools/p67-cli/bin/p67"
else
    note "CLI binary not built yet - run 'make install-cli'"
fi

section "CLI Connection"
if command -v p67 &>/dev/null; then
    if p67 connection list &>/dev/null; then
        connections=$(p67 connection list 2>/dev/null)
        if echo "$connections" | grep -q "p67"; then
            ok "CLI connection 'p67' is configured"
        else
            note "No 'p67' connection - run: p67 connection add p67 --endpoint http://localhost:3002"
        fi
    else
        note "Could not list CLI connections"
    fi
else
    note "Skipping connection checks (p67 CLI not installed)"
fi

section "Node Modules"
if [[ -d "$P67_ROOT/node_modules" ]]; then
    ok "Root node_modules exists"
else
    bad "Root node_modules missing - run 'pnpm install'"
fi

echo ""
echo "---"
echo -e "Results: ${GREEN}$pass passed${NC}, ${RED}$fail failed${NC}, ${YELLOW}$warn warnings${NC}"

if ((fail > 0)); then
    echo ""
    echo "Fix the FAIL items above, then re-run this script."
    exit 1
elif ((warn > 0)); then
    echo ""
    echo "Warnings are generally OK if you haven't completed the install yet."
fi
