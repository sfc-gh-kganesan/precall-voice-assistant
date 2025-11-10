#!/bin/bash
# Start all required MCP services for DDA Agent
# This script starts the DDA MCP server and Glean proxy in separate terminal windows

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}DDA Agent Services Startup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if we're in the troubleshooting directory
if [ ! -f "app/mcp_server.py" ] || [ ! -f "app/glean_proxy.py" ]; then
    echo -e "${RED}Error: Must be run from the troubleshooting directory${NC}"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' is not installed${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Detect OS for terminal handling
OS="$(uname -s)"

echo -e "${YELLOW}Starting services...${NC}"
echo ""

case "${OS}" in
    Darwin*)
        # macOS - use osascript to open new Terminal windows
        echo -e "${GREEN}[1/2]${NC} Starting DDA MCP Server..."
        osascript <<EOF
tell application "Terminal"
    do script "cd $(pwd) && echo 'Starting DDA MCP Server...' && uv run app/mcp_server.py"
    activate
end tell
EOF
        sleep 2

        echo -e "${GREEN}[2/2]${NC} Starting Glean Proxy (OAuth will open in browser)..."
        osascript <<EOF
tell application "Terminal"
    do script "cd $(pwd) && echo 'Starting Glean Proxy...' && uv run app/glean_proxy.py"
    activate
end tell
EOF
        ;;

    Linux*)
        # Linux - try common terminal emulators
        if command -v gnome-terminal &> /dev/null; then
            TERMINAL="gnome-terminal --"
        elif command -v xterm &> /dev/null; then
            TERMINAL="xterm -hold -e"
        elif command -v konsole &> /dev/null; then
            TERMINAL="konsole -e"
        else
            echo -e "${RED}Error: No supported terminal emulator found${NC}"
            echo "Please run services manually (see README_SERVICES.md)"
            exit 1
        fi

        echo -e "${GREEN}[1/2]${NC} Starting DDA MCP Server..."
        $TERMINAL bash -c "cd $(pwd) && echo 'Starting DDA MCP Server...' && uv run app/mcp_server.py" &
        sleep 2

        echo -e "${GREEN}[2/2]${NC} Starting Glean Proxy (OAuth will open in browser)..."
        $TERMINAL bash -c "cd $(pwd) && echo 'Starting Glean Proxy...' && uv run app/glean_proxy.py" &
        ;;

    *)
        echo -e "${RED}Unsupported OS: ${OS}${NC}"
        echo "Please run services manually (see README_SERVICES.md)"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✓ Services are starting in separate terminal windows${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Wait for OAuth flow in Glean Proxy window (browser will open)"
echo "2. Complete authentication in your browser"
echo "3. Wait for both services to show 'Ready' or 'Running'"
echo "4. Run the agent:"
echo -e "   ${GREEN}uv run app/agent_cli.py${NC}"
echo ""
echo -e "${YELLOW}To stop services:${NC}"
echo "- Close the terminal windows"
echo "- Or press Ctrl+C in each terminal"
echo ""
echo "For manual instructions, see: ${GREEN}README_SERVICES.md${NC}"
