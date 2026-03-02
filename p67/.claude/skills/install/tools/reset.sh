#!/usr/bin/env bash
# reset.sh - Tear down P67 local dev environment for a clean reinstall
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
P67_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

echo -e "${YELLOW}P67 Full Reset${NC}"
echo "This will remove containers, volumes, generated configs, and build artifacts."
echo "Root: $P67_ROOT"
echo ""

read -p "Continue? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""

# 1. Stop and remove Docker containers + volumes
echo -e "${YELLOW}[1/5]${NC} Stopping Docker containers and removing volumes..."
cd "$P67_ROOT"
if docker compose ps -q &>/dev/null; then
    docker compose down -v --remove-orphans 2>/dev/null || true
    echo -e "  ${GREEN}Done${NC}"
else
    echo "  No containers to stop"
fi

# 2. Remove generated .env files
echo -e "${YELLOW}[2/5]${NC} Removing generated .env files..."
for envfile in \
    "$P67_ROOT/.env" \
    "$P67_ROOT/packages/db/.env" \
    "$P67_ROOT/services/controld/.env" \
    "$P67_ROOT/tools/p67-cli/.env"; do
    if [[ -f "$envfile" ]]; then
        rm "$envfile"
        echo "  Removed ${envfile#$P67_ROOT/}"
    fi
done

# 3. Remove generated Makefile (from configure.sh)
echo -e "${YELLOW}[3/5]${NC} Removing generated Makefile..."
if [[ -f "$P67_ROOT/Makefile" ]]; then
    rm "$P67_ROOT/Makefile"
    echo "  Removed Makefile"
else
    echo "  No generated Makefile found"
fi

# 4. Clean CLI build artifacts
echo -e "${YELLOW}[4/5]${NC} Cleaning CLI build artifacts..."
if [[ -f "$P67_ROOT/tools/p67-cli/bin/p67" ]]; then
    rm "$P67_ROOT/tools/p67-cli/bin/p67"
    echo "  Removed tools/p67-cli/bin/p67"
fi

# Remove symlink if it exists in common locations
for dir in /usr/local/bin "$HOME/.local/bin"; do
    if [[ -L "$dir/p67" ]]; then
        rm "$dir/p67"
        echo "  Removed symlink $dir/p67"
    fi
done

# 5. Clean controld local storage
echo -e "${YELLOW}[5/5]${NC} Cleaning local storage..."
if [[ -d "$P67_ROOT/services/controld/.data_root" ]]; then
    rm -rf "$P67_ROOT/services/controld/.data_root"
    echo "  Removed services/controld/.data_root"
fi

echo ""
echo -e "${GREEN}Reset complete.${NC} You can now re-run the install from Step 1:"
echo "  cd $P67_ROOT && ./configure.sh"
echo "  make dev"
