"""
Debug script to inspect raw GitHub MCP response for get_file_contents

This script helps diagnose why get_file_contents returns only a SHA
instead of the actual file content.

Usage:
    uv run agentsim/backend/code_agent/test_github_mcp_raw.py
"""

import asyncio
import json
import logging
from fastmcp import Client

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
PROXY_URL = "http://localhost:8003/mcp"
TEST_REPO_OWNER = "snowflakedb"
TEST_REPO_NAME = "aura"
TEST_FILE_PATH = "support-data-agent/README.md"
TEST_REF = "main"


async def inspect_raw_response():
    """Inspect the raw response from get_file_contents."""
    print("=" * 80)
    print("GITHUB MCP RAW RESPONSE INSPECTOR")
    print("=" * 80)
    print(f"\nProxy URL: {PROXY_URL}")
    print(f"Testing: {TEST_REPO_OWNER}/{TEST_REPO_NAME}/{TEST_FILE_PATH}")
    print()

    try:
        # Create FastMCP client
        config = {"mcpServers": {"github-proxy": {"url": PROXY_URL}}}

        async with Client(config) as client:
            logger.info("Connected to GitHub MCP proxy")

            # Prepare parameters
            params = {
                "owner": TEST_REPO_OWNER,
                "repo": TEST_REPO_NAME,
                "path": TEST_FILE_PATH,
                "ref": TEST_REF,
            }

            print("Calling get_file_contents with params:")
            print(json.dumps(params, indent=2))
            print()

            # Call the tool
            result = await client.call_tool("get_file_contents", params)

            # Inspect the full result object
            print("=" * 80)
            print("RAW RESULT OBJECT")
            print("=" * 80)
            print(f"Type: {type(result)}")
            print(f"Dir: {[attr for attr in dir(result) if not attr.startswith('_')]}")
            print()

            # Check for isError
            if hasattr(result, "isError"):
                print(f"isError: {result.isError}")
            if hasattr(result, "is_error"):
                print(f"is_error: {result.is_error}")
            print()

            # Inspect content field
            if hasattr(result, "content"):
                print("=" * 80)
                print("CONTENT FIELD")
                print("=" * 80)
                print(f"Type: {type(result.content)}")
                print(f"Length: {len(result.content) if result.content else 0}")
                print()

                if result.content:
                    for i, content_block in enumerate(result.content):
                        print(f"--- Content Block {i} ---")
                        print(f"Type: {type(content_block)}")
                        print(
                            f"Dir: {[attr for attr in dir(content_block) if not attr.startswith('_')]}"
                        )
                        print()

                        # Check block type
                        if hasattr(content_block, "type"):
                            print(f"Block type attribute: {content_block.type}")
                            print()

                        # Check for RESOURCE type (this is where file content is!)
                        if (
                            hasattr(content_block, "type")
                            and content_block.type == "resource"
                        ):
                            print(
                                "\u2713\u2713\u2713 FOUND RESOURCE BLOCK! \u2713\u2713\u2713"
                            )
                            if hasattr(content_block, "resource"):
                                resource = content_block.resource
                                print(f"Resource type: {type(resource)}")
                                print(
                                    f"Resource dir: {[attr for attr in dir(resource) if not attr.startswith('_')]}"
                                )

                                if hasattr(resource, "uri"):
                                    print(f"Resource URI: {resource.uri}")
                                if hasattr(resource, "mimeType"):
                                    print(f"Resource MIME type: {resource.mimeType}")
                                if hasattr(resource, "text"):
                                    text = resource.text
                                    print(
                                        f"Resource text length: {len(text) if text else 0}"
                                    )
                                    print("Resource text preview (first 500 chars):")
                                    print("-" * 80)
                                    print(text[:500] if text else "(empty)")
                                    print("-" * 80)
                            print()

                        # Check for text attribute
                        if hasattr(content_block, "text"):
                            text = content_block.text
                            print("Has 'text' attribute!")
                            print(f"Text type: {type(text)}")
                            print(f"Text length: {len(text) if text else 0}")
                            print("Text preview (first 200 chars):")
                            print("-" * 80)
                            print(text[:200] if text else "(empty)")
                            print("-" * 80)

                        # Check for other common attributes
                        for attr in [
                            "content",
                            "data",
                            "value",
                            "body",
                            "file_content",
                        ]:
                            if hasattr(content_block, attr):
                                val = getattr(content_block, attr)
                                print(f"Has '{attr}' attribute!")
                                print(f"  Type: {type(val)}")
                                if isinstance(val, (str, bytes)):
                                    print(f"  Length: {len(val)}")
                                    print(f"  Preview: {str(val)[:200]}")

                        # Try to convert to dict
                        if hasattr(content_block, "__dict__"):
                            print(f"__dict__: {content_block.__dict__}")

                        # Try to convert to string
                        print("str() representation:")
                        print(str(content_block)[:500])
                        print()

            # Check for other common fields
            print("=" * 80)
            print("OTHER FIELDS")
            print("=" * 80)
            for attr in ["metadata", "meta", "data", "result", "response", "output"]:
                if hasattr(result, attr):
                    val = getattr(result, attr)
                    print(f"{attr}: {val}")
            print()

            # Try listing resources
            print("=" * 80)
            print("MCP RESOURCES CHECK")
            print("=" * 80)
            try:
                resources = await client.list_resources()
                print(f"Found {len(resources) if resources else 0} resources")
                if resources:
                    for i, resource in enumerate(resources[:5]):  # Show first 5
                        print(f"{i}. {resource}")
            except Exception as e:
                print(f"Could not list resources: {e}")
            print()

            return result

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error("Failed to inspect response", exc_info=True)
        return None


async def test_different_files():
    """Test with different file types to see if behavior differs."""
    test_files = [
        ("support-data-agent/README.md", "Markdown file"),
        ("support-data-agent/troubleshooting/app/main.py", "Python file"),
        ("support-data-agent/.gitignore", "Small text file"),
    ]

    config = {"mcpServers": {"github-proxy": {"url": PROXY_URL}}}

    print("\n" + "=" * 80)
    print("TESTING DIFFERENT FILE TYPES")
    print("=" * 80)

    async with Client(config) as client:
        for file_path, description in test_files:
            print(f"\nTesting: {description} - {file_path}")
            try:
                params = {
                    "owner": TEST_REPO_OWNER,
                    "repo": TEST_REPO_NAME,
                    "path": file_path,
                    "ref": TEST_REF,
                }

                result = await client.call_tool("get_file_contents", params)

                if result.content and len(result.content) > 0:
                    content_block = result.content[0]
                    if hasattr(content_block, "text"):
                        text = content_block.text
                        print(f"  ✓ Got text (length: {len(text) if text else 0})")
                        print(f"  Preview: {text[:100]}...")
                    else:
                        print("  ✗ No 'text' attribute")
                else:
                    print("  ✗ No content")

            except Exception as e:
                print(f"  ✗ Error: {e}")

            await asyncio.sleep(1)  # Rate limiting


def main():
    """Main entry point."""
    print("Starting GitHub MCP raw response inspection...\n")

    # Run detailed inspection
    asyncio.run(inspect_raw_response())

    # Test different files
    asyncio.run(test_different_files())

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
