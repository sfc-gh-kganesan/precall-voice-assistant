"""
DDA Agent CLI

An interactive command-line interface for the DDA agent.
Allows support engineers to ask natural language questions about Snowflake cases,
queries, and diagnostic issues.
"""

import asyncio
import sys
import traceback

from pydantic_ai import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)

from app.agent import create_dda_agent


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal formatting."""

    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


async def stream_cli_response(agent, prompt: str):
    """
    Stream agent response to terminal with real-time text and tool execution status.

    Args:
        agent: The PydanticAI agent instance
        prompt: User's question/query
    """
    print()  # Start with a newline

    full_content = ""
    tools_pending = 0

    async for event in agent.run_stream_events(prompt):
        # Track tool call start
        if isinstance(event, FunctionToolCallEvent):
            tools_pending += 1
            tool_name = event.part.tool_name
            print(
                f"\n{Colors.YELLOW}🔧 Calling tool: {tool_name}...{Colors.RESET}",
                flush=True,
            )
            continue

        # Track tool call completion
        if isinstance(event, FunctionToolResultEvent):
            tools_pending -= 1
            tool_name = event.result.tool_name
            print(
                f"{Colors.GREEN}✅ Tool completed: {tool_name}{Colors.RESET}",
                flush=True,
            )

            # Reset accumulator after all tools complete
            if tools_pending == 0:
                full_content = ""
                print()  # Extra newline before final answer
            continue

        # Extract initial text content from PartStartEvent
        if isinstance(event, PartStartEvent):
            if hasattr(event.part, "content"):
                text_content = event.part.content
                if isinstance(text_content, str) and text_content:
                    full_content += text_content
                    print(text_content, end="", flush=True)

        # Extract streaming text content from PartDeltaEvent
        if isinstance(event, PartDeltaEvent):
            if isinstance(event.delta, TextPartDelta):
                text_content = event.delta.content_delta
                if text_content:
                    full_content += text_content
                    print(text_content, end="", flush=True)

    print()  # Final newline after response


async def run_cli(
    model_name: str = "claude-4-sonnet", server_url: str = "http://localhost:8000/mcp"
):
    """
    Run the interactive CLI for the DDA agent.

    Args:
        model_name: The Snowflake Cortex model to use
        server_url: URL of the DDA MCP server
    """
    print("=" * 70)
    print("DDA Support Agent - Interactive CLI")
    print("=" * 70)
    print(f"\nModel: {model_name} (via Snowflake Cortex)")
    print(f"MCP Server: {server_url}")
    print("\nConnecting to MCP server...")

    try:
        # Create the agent
        agent = create_dda_agent(model_name=model_name, mcp_server_url=server_url)

        print("\nAgent ready! Type your questions or commands:")
        print("  - Ask about cases: 'Get details for case 01172497'")
        print("  - Analyze locks: 'Analyze transaction locks for query 01c00d3d...'")
        print("  - Search cases: 'Find open performance cases'")
        print("  - Type 'help' for more examples")
        print("  - Type 'exit' or 'quit' to end")
        print("=" * 70)

        # Start the REPL loop
        while True:
            try:
                # Get user input
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("\nGoodbye!")
                    break

                if user_input.lower() == "help":
                    print_help()
                    continue

                # Send query to agent with streaming
                await stream_cli_response(agent, user_input)

            except KeyboardInterrupt:
                print(
                    "\n\nInterrupted. Type 'exit' to quit or continue asking questions."
                )
                continue
            except Exception as e:
                print(f"\nError: {e}")
                print("\nFull traceback:")
                traceback.print_exc()
                print("\nPlease try again or type 'exit' to quit.")

    except Exception as e:
        print(f"\nFailed to initialize agent: {e}")
        print("\nMake sure:")
        print("  1. The MCP server is running (python app/mcp_server.py)")
        print("  2. Your Snowflake credentials are set in .env")
        print("  3. The server URL is correct")
        sys.exit(1)


def print_help():
    """Print help information with example queries."""
    print("\n" + "=" * 70)
    print("HELP - Example Queries")
    print("=" * 70)
    print("\nCase Operations:")
    print("  - Get details for case 01172497")
    print("  - Show me queries for case 01172497")
    print("  - Search for open cases about performance issues")
    print("\nQuery Analysis:")
    print(
        "  - Analyze transaction locks for query 01c00d3d-0a0c-f195-0196-2e015312a02b"
    )
    print("  - Investigate why query <query_id> is slow")
    print("  - Show me queries with lock issues")
    print("\nTSW Diagnostics:")
    print("  - Check for RBAC issues in deployment azeastus2prod account 103982")
    print("  - Analyze compilation issues for case 01172497")
    print("  - Look for authentication problems in account <account_id>")
    print("\nWarehouse & Account:")
    print("  - Show warehouse metrics for <warehouse_name>")
    print("  - Get account information for <account_id>")
    print("=" * 70)


def main():
    """Main entry point for the CLI."""
    # Parse command line arguments (optional)
    model_name = "claude-4-sonnet"  # Default Cortex model
    server_url = "http://localhost:8000/mcp"

    if len(sys.argv) > 1:
        model_name = sys.argv[1]
    if len(sys.argv) > 2:
        server_url = sys.argv[2]

    # Run the async CLI
    asyncio.run(run_cli(model_name=model_name, server_url=server_url))


if __name__ == "__main__":
    main()
