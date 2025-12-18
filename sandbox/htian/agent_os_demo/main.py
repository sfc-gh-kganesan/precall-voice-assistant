"""Agent OS Demo - Main entry point for CLI usage."""

import argparse


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Agent OS Demo CLI")
    parser.add_argument("--version", action="version", version="0.1.0")
    parser.add_argument("--prompt", type=str, help="Prompt to send to the agent")

    args = parser.parse_args()

    if args.prompt:
        print(f"Processing prompt: {args.prompt}")
        # Placeholder for agent invocation
        print("Agent response: This is a demo response.")
    else:
        print("Agent OS Demo")
        print("Use --prompt to interact with the agent")
        print("Use 'just dev' to start the development server")


if __name__ == "__main__":
    main()
