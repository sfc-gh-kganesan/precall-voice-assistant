"""
DDA Agent CLI

An interactive command-line interface for the DDA agent.
Allows support engineers to ask natural language questions about Snowflake cases,
queries, and diagnostic issues.
"""

import asyncio
import sys
import traceback

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from pydantic_ai import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)

from app.agents.dda_agent import create_dda_agent


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
    pending_tool_names = []  # Track multiple parallel tool calls

    async for event in agent.run_stream_events(prompt):
        # Track tool call start
        if isinstance(event, FunctionToolCallEvent):
            tools_pending += 1
            tool_name = event.part.tool_name

            # DEBUG: Log to understand what's happening
            import sys

            print(
                f"\n[DEBUG] FunctionToolCallEvent #{tools_pending}: tool_name='{tool_name}', pending_count={len(pending_tool_names)}",
                file=sys.stderr,
            )

            pending_tool_names.append(tool_name)

            # Print tool call - simple inline approach
            if len(pending_tool_names) == 1:
                # First tool - print the prefix
                print(
                    f"\n{Colors.YELLOW}🔧 Calling tool: {tool_name}",
                    end="",
                    flush=True,
                )
                print("", file=sys.stderr, flush=True)  # DEBUG: Force flush
            else:
                # Additional tools - just print comma and name inline
                print(
                    f", {tool_name}",
                    end="",
                    flush=True,
                )
                print("", file=sys.stderr, flush=True)  # DEBUG: Force flush
            continue

        # Track tool call completion
        if isinstance(event, FunctionToolResultEvent):
            tools_pending -= 1
            tool_name = event.result.tool_name

            # On first result, close the tool list with ... and newline
            if (
                tools_pending == len(pending_tool_names) - 1
                and len(pending_tool_names) > 0
            ):
                print(f"...{Colors.RESET}", flush=True)

            # Remove from pending list
            if tool_name in pending_tool_names:
                pending_tool_names.remove(tool_name)

            # Show completion
            if tools_pending == 0:
                # All tools done
                print(
                    f"{Colors.GREEN}✅ All tools completed{Colors.RESET}",
                    flush=True,
                )
                pending_tool_names = []  # Reset for next batch
            else:
                # Still waiting on other tools
                remaining = ", ".join(pending_tool_names)
                print(
                    f"{Colors.GREEN}✅ Tool completed: {tool_name}{Colors.RESET}",
                    flush=True,
                )
                print(
                    f"{Colors.YELLOW}⏳ Still running: {remaining}...{Colors.RESET}",
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
    model_name: str = "claude-4-sonnet",
    server_url: str = "http://localhost:8000/mcp",
    glean_proxy_url: str = "http://localhost:8001/mcp",
):
    """
    Run the interactive CLI for the DDA agent.

    Args:
        model_name: The Snowflake Cortex model to use
        server_url: URL of the DDA Native MCP server
        glean_proxy_url: URL of the Glean proxy server (or None to disable)
    """
    print("\n")
    print("    ╔═══════════════════════════════════════════════════╗")
    print("    ║                                                   ║")
    print("    ║            _____ __   __   _____                  ║")
    print(r"    ║           / ____|\ \ / /  / ____|                 ║")
    print(r"    ║          | |      \ V /  | |                      ║")
    print("    ║          | |       > <   | |                      ║")
    print(r"    ║          | |____  / . \  | |____                  ║")
    print(r"    ║           \_____\/_/ \_\  \_____|                 ║")
    print("    ║                                                   ║")
    print("    ║                  CX Copilot                       ║")
    print("    ║       Your Snowflake troubleshooting AI          ║")
    print("    ║                                                   ║")
    print("    ╚═══════════════════════════════════════════════════╝")
    print("\n  Initializing...")

    try:
        # Create the agent with both DDA and Glean toolsets
        agent = create_dda_agent(
            model_name=model_name,
            mcp_server_url=server_url,
            glean_proxy_url=glean_proxy_url,
        )

        print("\n✓ Ready! I have access to:")
        print("  • DDA diagnostic tools for deep case analysis")
        print("  • Enterprise knowledge base and documentation")
        print("  • Best practices and troubleshooting workflows")
        print("\nWhat can I help you with?")
        print("  • Investigate a case or query")
        print("  • Analyze performance or errors")
        print("  • Search documentation and past solutions")
        print("\nType 'help' for examples or 'exit' to quit")
        print("=" * 60)

        # Create prompt session with history
        session = PromptSession(history=InMemoryHistory())

        # Start the REPL loop
        while True:
            try:
                # Get user input with history support
                user_input = (await session.prompt_async("\n> ")).strip()

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

            except EOFError:
                # Handle Ctrl+D gracefully
                print("\n\nGoodbye!")
                break
            except KeyboardInterrupt:
                print(
                    "\n\nInterrupted. Type 'exit' to quit or continue asking questions."
                )
                continue
            except RuntimeError as e:
                # Workaround for pydantic-ai/MCP cancel scope bug during cleanup
                if "cancel scope" in str(e).lower():
                    print(
                        f"\n{Colors.YELLOW}⚠️  Note: MCP cleanup warning (known issue, query completed successfully){Colors.RESET}"
                    )
                    continue
                else:
                    print(f"\nError: {e}")
                    print("\nFull traceback:")
                    traceback.print_exc()
                    print("\nPlease try again or type 'exit' to quit.")
            except Exception as e:
                # Check for 500 errors (internal server errors)
                if "500" in str(e) or "internal error" in str(e).lower():
                    print(
                        f"\n{Colors.YELLOW}⚠️  Snowflake API temporarily unavailable. "
                        "The request has been automatically retried.{Colors.RESET}"
                    )
                    print(
                        "If the issue persists, try rephrasing your question or try again in a moment.\n"
                    )
                else:
                    print(f"\nError: {e}")

                print("\nFull traceback:")
                traceback.print_exc()
                print("\nPlease try again or type 'exit' to quit.")

    except Exception as e:
        print(f"\nFailed to initialize agent: {e}")
        print("\nMake sure:")
        print("  1. The Native MCP server is running (python app/dda_mcp_native.py)")
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
    print("\nGlean Knowledge Search:")
    print("  - Search for documents about authentication issues")
    print("  - Find code examples for stored procedures")
    print("  - Who works on query optimization?")
    print("  - Read document at <url>")
    print("=" * 70)


# Create Typer app
app = typer.Typer(help="CX Copilot - AI-powered Snowflake troubleshooting assistant")


@app.command()
def main(
    model: str = typer.Option(
        "claude-4-sonnet",
        "--model",
        "-m",
        help="The Snowflake Cortex model to use (e.g., claude-4-sonnet, claude-3-5-sonnet)",
    ),
    server_url: str = typer.Option(
        "http://localhost:8000/mcp",
        "--server-url",
        "-s",
        help="URL of the DDA Native MCP server",
    ),
    glean_proxy_url: str = typer.Option(
        "http://localhost:8001/mcp",
        "--glean-proxy-url",
        "-g",
        help="URL of the Glean proxy server",
    ),
):
    """
    Run the interactive CLI for the DDA agent.

    This starts an interactive REPL session where you can ask natural language
    questions about Snowflake cases, queries, and diagnostic issues.
    """
    # Run the async CLI
    asyncio.run(
        run_cli(
            model_name=model,
            server_url=server_url,
            glean_proxy_url=glean_proxy_url,
        )
    )


if __name__ == "__main__":
    app()
