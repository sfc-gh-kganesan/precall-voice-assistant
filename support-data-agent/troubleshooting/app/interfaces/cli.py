"""
DDA Agent CLI

An interactive command-line interface for the DDA agent API.
Allows support engineers to ask natural language questions about Snowflake cases,
queries, and diagnostic issues via the agent API's streaming endpoint.
"""

import asyncio
import json
import sys
import traceback
import uuid

import httpx
import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal formatting."""

    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


async def stream_cli_response_from_api(api_url: str, prompt: str, conversation_id: str):
    """
    Stream agent response from API to terminal with real-time text and tool execution status.

    Args:
        api_url: Base URL of the agent API (e.g., http://localhost:8002)
        prompt: User's question/query
        conversation_id: Unique conversation identifier for history tracking
    """
    print()  # Start with a newline

    full_content = ""
    tools_pending = 0
    pending_tool_names = []  # Track multiple parallel tool calls

    # Prepare request payload
    payload = {
        "message": prompt,
        "stream": True,
        "conversation_id": conversation_id,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{api_url}/query",
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as response:
                response.raise_for_status()

                # Parse Server-Sent Events
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # Parse SSE format: "event: <type>\ndata: <json>\n\n"
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        # Handle different event types
                        if event_type == "tool_call":
                            # Tool started
                            tools_pending += 1
                            tool_name = data.get("tool", "unknown")
                            pending_tool_names.append(tool_name)

                            # Print tool call
                            if len(pending_tool_names) == 1:
                                print(
                                    f"\n{Colors.YELLOW}🔧 Calling tool: {tool_name}",
                                    end="",
                                    flush=True,
                                )
                            else:
                                print(f", {tool_name}", end="", flush=True)

                        elif event_type == "tool_result":
                            # Tool completed
                            tools_pending -= 1
                            tool_name = data.get("tool", "unknown")

                            # On first result, close the tool list
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
                                print(
                                    f"{Colors.GREEN}✅ All tools completed{Colors.RESET}",
                                    flush=True,
                                )
                                pending_tool_names = []
                                full_content = ""
                                print()  # Extra newline before final answer

                        elif event_type == "text_delta":
                            # Streaming text content
                            text_content = data.get("content", "")
                            if text_content:
                                full_content += text_content
                                print(text_content, end="", flush=True)

                        elif event_type == "final":
                            # Final response (redundant if we've been streaming, but good for validation)
                            pass

                        elif event_type == "error":
                            # Error from API
                            error_msg = data.get("error", "Unknown error")
                            print(
                                f"\n{Colors.RED}Error from API: {error_msg}{Colors.RESET}"
                            )
                            break

    except httpx.HTTPStatusError as e:
        print(f"\n{Colors.RED}HTTP Error: {e.response.status_code}{Colors.RESET}")
        print(f"Details: {e.response.text}")
    except httpx.RequestError as e:
        print(
            f"\n{Colors.RED}Connection Error: Could not connect to agent API at {api_url}{Colors.RESET}"
        )
        print(f"Details: {str(e)}")
        print("\nMake sure the agent API is running:")
        print("  docker-compose up")
        print("  OR manually: uv run app/interfaces/api.py")
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}")
        traceback.print_exc()

    print()  # Final newline after response


async def run_cli(
    api_url: str = "http://localhost:8002",
    conversation_id: str = None,
):
    """
    Run the interactive CLI for the DDA agent.

    Args:
        api_url: Base URL of the agent API
        conversation_id: Optional conversation ID for maintaining history across sessions
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
    print("\n  Connecting to agent API...")

    # Generate conversation ID if not provided
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    # Test API connection
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{api_url}/health")
            response.raise_for_status()
            health = response.json()

        print(f"\n✓ Connected to agent API at {api_url}")
        print(f"  Conversation ID: {conversation_id}")
        print("\n✓ Agent has access to:")
        print("  • DDA diagnostic tools for deep case analysis")
        print("  • Enterprise knowledge base and documentation")
        print("  • Best practices and troubleshooting workflows")
        print("\nWhat can I help you with?")
        print("  • Investigate a case or query")
        print("  • Analyze performance or errors")
        print("  • Search documentation and past solutions")
        print("\nType 'help' for examples, 'clear' to reset history, or 'exit' to quit")
        print("=" * 60)

    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        print(
            f"\n{Colors.RED}Failed to connect to agent API at {api_url}{Colors.RESET}"
        )
        print(f"Error: {str(e)}")
        print("\nMake sure the agent API is running:")
        print("  docker-compose up")
        print("  OR manually: uv run app/interfaces/api.py")
        sys.exit(1)

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

            if user_input.lower() == "clear":
                # Clear conversation history
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.delete(
                            f"{api_url}/conversations/{conversation_id}/history"
                        )
                        response.raise_for_status()
                    print(f"{Colors.GREEN}✓ Conversation history cleared{Colors.RESET}")
                except Exception as e:
                    print(
                        f"{Colors.YELLOW}Warning: Could not clear history: {str(e)}{Colors.RESET}"
                    )
                continue

            # Send query to agent API with streaming
            await stream_cli_response_from_api(api_url, user_input, conversation_id)

        except EOFError:
            # Handle Ctrl+D gracefully
            print("\n\nGoodbye!")
            break
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit or continue asking questions.")
            continue
        except Exception as e:
            print(f"\n{Colors.RED}Error: {str(e)}{Colors.RESET}")
            print("\nFull traceback:")
            traceback.print_exc()
            print("\nPlease try again or type 'exit' to quit.")


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
    print("\nSpecial Commands:")
    print("  - clear : Clear conversation history and start fresh")
    print("  - help  : Show this help message")
    print("  - exit  : Quit the CLI")
    print("=" * 70)


# Create Typer app
app = typer.Typer(help="CX Copilot - AI-powered Snowflake troubleshooting assistant")


@app.command()
def main(
    api_url: str = typer.Option(
        "http://localhost:8002",
        "--api-url",
        "-a",
        help="Base URL of the agent API",
    ),
    conversation_id: str = typer.Option(
        None,
        "--conversation-id",
        "-c",
        help="Conversation ID for maintaining history across sessions (auto-generated if not provided)",
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
            api_url=api_url,
            conversation_id=conversation_id,
        )
    )


if __name__ == "__main__":
    app()
