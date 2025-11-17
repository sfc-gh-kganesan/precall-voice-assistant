"""
Test script for GitHub MCP get_file_contents tool

This script tests the get_file_contents tool through the GitHub MCP proxy server.
It fetches files from the remote GitHub repository snowflakedb/aura.

Prerequisites:
    1. GitHub proxy must be running: uv run agentsim/backend/code_agent/github_proxy.py
    2. GITHUB_TOKEN must be set in .env file

Usage:
    python agentsim/backend/code_agent/test_get_file_contents.py
"""

import asyncio
import logging
import sys
from typing import Optional

from fastmcp import Client

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
PROXY_URL = "http://localhost:8003/mcp"
TARGET_REPO_OWNER = "snowflakedb"
TARGET_REPO_NAME = "aura"


async def test_get_file_contents(
    owner: str, repo: str, path: str, ref: Optional[str] = None, test_name: str = "Test"
) -> bool:
    """
    Test the get_file_contents tool with specific parameters.

    Args:
        owner: Repository owner (e.g., "snowflakedb")
        repo: Repository name (e.g., "aura")
        path: File path in the repository
        ref: Optional branch/tag/commit reference
        test_name: Name for this test case

    Returns:
        True if test passed, False otherwise
    """
    print(f"\n{'=' * 70}")
    print(f"TEST: {test_name}")
    print(f"{'=' * 70}")
    print(f"Repository: {owner}/{repo}")
    print(f"Path: {path}")
    print(f"Ref: {ref or '(default branch)'}")
    print()

    try:
        # Create FastMCP client connected to the proxy
        config = {"mcpServers": {"github-proxy": {"url": PROXY_URL}}}

        async with Client(config) as client:
            logger.info("Connected to GitHub MCP proxy")

            # Prepare parameters
            params = {"owner": owner, "repo": repo, "path": path}

            # Add ref if specified
            if ref:
                params["ref"] = ref

            logger.info(f"Calling get_file_contents with params: {params}")

            # Call the tool
            result = await client.call_tool("get_file_contents", params)

            # Extract content from result
            if result.content:
                content_block = result.content[0]
                if hasattr(content_block, "text"):
                    file_content = content_block.text
                else:
                    file_content = str(content_block)

                # Display results
                print("✓ SUCCESS!")
                print("\nFile content preview (first 500 chars):")
                print("-" * 70)
                print(file_content[:500])
                if len(file_content) > 500:
                    print(f"\n... ({len(file_content) - 500} more characters)")
                print("-" * 70)
                print(f"\nTotal content length: {len(file_content)} characters")

                return True
            else:
                print("✗ FAILED: No content returned")
                return False

    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        logger.error("Error details:", exc_info=True)

        # Provide helpful hints based on error type
        error_str = str(e)
        if "Connection" in error_str or "refused" in error_str:
            print("\n💡 Hint: Make sure the GitHub proxy is running:")
            print("   uv run agentsim/backend/code_agent/github_proxy.py")
        elif "404" in error_str:
            print("\n💡 Hint: File not found. Check the repository, path, and branch.")
        elif "401" in error_str or "403" in error_str:
            print("\n💡 Hint: Authentication error. Check your GITHUB_TOKEN in .env")

        return False


async def run_all_tests():
    """Run all test cases for get_file_contents."""
    print("=" * 70)
    print("GET_FILE_CONTENTS TEST SUITE")
    print("=" * 70)
    print(f"Proxy URL: {PROXY_URL}")
    print(f"Target Repository: {TARGET_REPO_OWNER}/{TARGET_REPO_NAME}")
    print()

    results = []

    # Test 1: Fetch README.md from main branch
    results.append(
        await test_get_file_contents(
            owner=TARGET_REPO_OWNER,
            repo=TARGET_REPO_NAME,
            path="support-data-agent/README.md",
            ref="main",
            test_name="Fetch README.md from main branch",
        )
    )

    await asyncio.sleep(1)  # Rate limiting

    # Test 2: Fetch a Python file from troubleshooting directory
    results.append(
        await test_get_file_contents(
            owner=TARGET_REPO_OWNER,
            repo=TARGET_REPO_NAME,
            path="support-data-agent/troubleshooting/app/main.py",
            ref="main",
            test_name="Fetch main.py from troubleshooting app directory",
        )
    )

    await asyncio.sleep(1)  # Rate limiting

    # Test 3: Fetch from specific branch (checking if code_agent exists there)
    results.append(
        await test_get_file_contents(
            owner=TARGET_REPO_OWNER,
            repo=TARGET_REPO_NAME,
            path="support-data-agent/README.md",
            ref="alejandro/troubleshooting-two",
            test_name="Fetch README.md from alejandro/troubleshooting-two branch",
        )
    )

    await asyncio.sleep(1)  # Rate limiting

    # Test 4: Test error handling with invalid path
    results.append(
        await test_get_file_contents(
            owner=TARGET_REPO_OWNER,
            repo=TARGET_REPO_NAME,
            path="support-data-agent/this/path/does/not/exist.py",
            ref="main",
            test_name="Error handling - Invalid path",
        )
    )

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
    else:
        print(f"\n⚠ {total - passed} test(s) failed")

    return passed == total


async def run_interactive_test():
    """Run an interactive test where user provides parameters."""
    print("=" * 70)
    print("INTERACTIVE GET_FILE_CONTENTS TEST")
    print("=" * 70)
    print()

    # Get parameters from user
    owner = (
        input(f"Repository owner [{TARGET_REPO_OWNER}]: ").strip() or TARGET_REPO_OWNER
    )
    repo = input(f"Repository name [{TARGET_REPO_NAME}]: ").strip() or TARGET_REPO_NAME
    path = input("File path: ").strip()
    ref = input("Branch/tag/commit [default branch]: ").strip() or None

    if not path:
        print("Error: File path is required")
        return False

    return await test_get_file_contents(
        owner=owner, repo=repo, path=path, ref=ref, test_name="Interactive Test"
    )


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # Interactive mode
        success = asyncio.run(run_interactive_test())
    else:
        # Run all tests
        success = asyncio.run(run_all_tests())

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
