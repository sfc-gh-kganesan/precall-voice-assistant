#!/usr/bin/env python3
"""
Start all required MCP services for DDA Agent
Cross-platform Python script to manage service lifecycle
"""

import signal
import subprocess
import sys
import time
from pathlib import Path

# ANSI color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color

# Store process handles
processes = []


def print_header():
    """Print startup header"""
    print(f"{GREEN}========================================{NC}")
    print(f"{GREEN}DDA Agent Services Startup Script{NC}")
    print(f"{GREEN}========================================{NC}")
    print()


def check_prerequisites():
    """Check if required files and tools exist"""
    # Check if we're in the right directory
    if (
        not Path("app/mcp_server.py").exists()
        or not Path("app/glean_proxy.py").exists()
    ):
        print(f"{RED}Error: Must be run from the troubleshooting directory{NC}")
        print(f"Current directory: {Path.cwd()}")
        sys.exit(1)

    # Check if uv is installed
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{RED}Error: 'uv' is not installed{NC}")
        print("Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)


def cleanup(signum=None, frame=None):
    """Cleanup function to stop all services"""
    print(f"\n{YELLOW}Stopping all services...{NC}")
    for proc in processes:
        if proc.poll() is None:  # Process is still running
            print(f"  Stopping PID {proc.pid}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print(f"{GREEN}All services stopped{NC}")
    sys.exit(0)


def start_service(name, script_path, port):
    """Start a service in a subprocess"""
    print(f"{GREEN}[{len(processes) + 1}]{NC} Starting {name}...")
    try:
        proc = subprocess.Popen(
            ["uv", "run", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(proc)
        print(f"  {BLUE}PID: {proc.pid}, Port: {port}{NC}")
        return proc
    except Exception as e:
        print(f"{RED}Failed to start {name}: {e}{NC}")
        cleanup()
        sys.exit(1)


def main():
    """Main entry point"""
    print_header()
    check_prerequisites()

    # Register cleanup handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print(f"{YELLOW}Starting services...{NC}")
    print()

    # Start DDA MCP Server
    dda_proc = start_service("DDA MCP Server", "app/mcp_server.py", 8000)
    time.sleep(2)

    # Start Glean Proxy
    glean_proc = start_service("Glean Proxy", "app/glean_proxy.py", 8001)
    print(
        f"  {YELLOW}Note: OAuth browser window will open for Glean authentication{NC}"
    )
    time.sleep(3)

    # Start Agent API
    agent_api_proc = start_service("Agent API Server", "app/agent_api.py", 8002)
    time.sleep(2)

    print()
    print(f"{GREEN}✓ All services started{NC}")
    print()
    print(f"{YELLOW}Services running:{NC}")
    print(f"  - DDA MCP Server:    http://localhost:8000/mcp (PID: {dda_proc.pid})")
    print(f"  - Glean Proxy:       http://localhost:8001/mcp (PID: {glean_proc.pid})")
    print(f"  - Agent API:         http://localhost:8002 (PID: {agent_api_proc.pid})")
    print()
    print(f"{YELLOW}Next steps:{NC}")
    print("1. Complete OAuth authentication in the browser for Glean Proxy")
    print("2. Wait for all services to show 'Ready' or 'Running' in their logs")
    print("3. Test the API:")
    print(f"   {GREEN}uv run test_agent_api.py{NC}")
    print("   OR interact via CLI:")
    print(f"   {GREEN}uv run app/agent_cli.py{NC}")
    print()
    print(f"{YELLOW}Monitoring services... Press Ctrl+C to stop all services{NC}")
    print()

    # Monitor processes
    try:
        while True:
            # Check if any process died
            for proc in processes:
                if proc.poll() is not None:
                    print(f"{RED}Process {proc.pid} exited unexpectedly{NC}")
                    cleanup()
                    sys.exit(1)
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
