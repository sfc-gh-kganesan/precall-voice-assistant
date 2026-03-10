#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGE_JSON="$CLI_DIR/package.json"

usage() {
  echo "Usage: $0 [patch|minor|major]"
  echo ""
  echo "Prepares a p67-cli release by bumping the version, creating a release branch,"
  echo "committing the change, and pushing to origin."
  echo ""
  echo "Arguments:"
  echo "  patch   Bump the patch version (default)"
  echo "  minor   Bump the minor version"
  echo "  major   Bump the major version"
  exit 1
}

BUMP_TYPE="${1:-patch}"

if [[ "$BUMP_TYPE" != "patch" && "$BUMP_TYPE" != "minor" && "$BUMP_TYPE" != "major" ]]; then
  echo -e "${RED}Error: Invalid bump type '$BUMP_TYPE'${NC}"
  usage
fi

if [[ ! -f "$PACKAGE_JSON" ]]; then
  echo -e "${RED}Error: package.json not found at $PACKAGE_JSON${NC}"
  exit 1
fi

CURRENT_VERSION=$(node -p "require('$PACKAGE_JSON').version")
echo "Current version: $CURRENT_VERSION"

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

case "$BUMP_TYPE" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
BRANCH_NAME="release-p67-cli-${NEW_VERSION}"

echo -e "New version: ${GREEN}${NEW_VERSION}${NC}"
echo -e "Branch: ${GREEN}${BRANCH_NAME}${NC}"
echo ""

if git ls-remote --heads origin "$BRANCH_NAME" | grep -q "$BRANCH_NAME"; then
  echo -e "${RED}Error: Branch '$BRANCH_NAME' already exists on remote${NC}"
  exit 1
fi

read -rp "Proceed? (y/n): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

node -e "
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('$PACKAGE_JSON', 'utf8'));
pkg.version = '$NEW_VERSION';
fs.writeFileSync('$PACKAGE_JSON', JSON.stringify(pkg, null, 4) + '\n');
"

git checkout -b "$BRANCH_NAME"
git add "$PACKAGE_JSON"
git commit -m "chore(p67-cli): bump version to ${NEW_VERSION}"
git push -u origin "$BRANCH_NAME"

echo ""
echo -e "${GREEN}Release branch '${BRANCH_NAME}' created and pushed.${NC}"
echo ""
echo "Next steps:"
echo "  1. Go to GitHub Actions"
echo "  2. Select the 'p67 CLI - New Release' workflow"
echo "  3. Click 'Run workflow' on branch '${BRANCH_NAME}'"
echo "  4. Choose the release type (dev, beta, or prod)"
