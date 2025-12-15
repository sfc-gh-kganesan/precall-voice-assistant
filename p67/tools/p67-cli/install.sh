#!/usr/bin/env bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# File paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
P67_BIN="${SCRIPT_DIR}/bin/p67"

# Function to print colored messages
print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

# Load existing .env if it exists
if [[ -f "$ENV_FILE" ]]; then
    # Source the .env file to get P67_INSTALL_DIR
    set -a
    source "$ENV_FILE"
    set +a
fi

# Step 1: Prompt for install directory with default
DEFAULT_DIR="/usr/local/bin"
if [[ -n "${P67_INSTALL_DIR:-}" ]]; then
    echo "Current install directory: $P67_INSTALL_DIR"
    read -p "Install directory [${P67_INSTALL_DIR}]: " INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-$P67_INSTALL_DIR}"
else
    read -p "Install directory [${DEFAULT_DIR}]: " INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_DIR}"
fi

# Expand tilde if present
INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"

echo ""

# Step 2: Ensure the directory exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    print_error "Directory does not exist: $INSTALL_DIR"
    read -p "Would you like to create it? (y/n): " CREATE_DIR
    if [[ "$CREATE_DIR" =~ ^[Yy]$ ]]; then
        mkdir -p "$INSTALL_DIR" || {
            print_error "Failed to create directory: $INSTALL_DIR"
            exit 1
        }
        print_success "Created directory: $INSTALL_DIR"
    else
        print_error "Installation cancelled."
        exit 1
    fi
fi

# Verify the directory is writable
if [[ ! -w "$INSTALL_DIR" ]]; then
    print_error "Directory is not writable: $INSTALL_DIR"
    echo "You may need to run this script with sudo or choose a different directory."
    exit 1
fi

# Step 3: Check if directory is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    print_warning "The directory $INSTALL_DIR is not in your \$PATH"
    echo "You may need to add it to your PATH by adding this line to your shell profile:"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
    echo ""
fi

# Step 4: Save to .env file
echo $ENV_FILE
echo $INSTALL_DIR
echo "P67_INSTALL_DIR=\"$INSTALL_DIR\"" > "$ENV_FILE"
print_success "Saved install directory to $ENV_FILE"

# Step 6: Ensure ./bin/p67 exists
if [[ ! -f "$P67_BIN" ]]; then
    print_error "Source file does not exist: $P67_BIN"
    exit 1
fi

# Make sure the source file is executable
if [[ ! -x "$P67_BIN" ]]; then
    print_warning "Making $P67_BIN executable"
    chmod +x "$P67_BIN"
fi

# Step 7: Create symlink
SYMLINK_PATH="${INSTALL_DIR}/p67"

# Remove existing symlink or file if it exists
if [[ -L "$SYMLINK_PATH" ]]; then
    print_warning "Removing existing symlink: $SYMLINK_PATH"
    rm "$SYMLINK_PATH"
elif [[ -f "$SYMLINK_PATH" ]]; then
    print_warning "File already exists at $SYMLINK_PATH"
    read -p "Overwrite? (y/n): " OVERWRITE
    if [[ "$OVERWRITE" =~ ^[Yy]$ ]]; then
        rm "$SYMLINK_PATH"
    else
        print_error "Installation cancelled."
        exit 1
    fi
fi

# Create the symlink
ln -s "$P67_BIN" "$SYMLINK_PATH" || {
    print_error "Failed to create symlink"
    exit 1
}

print_success "Created symlink: $SYMLINK_PATH -> $P67_BIN"
echo ""
echo "Installation complete! You can now run: p67"
