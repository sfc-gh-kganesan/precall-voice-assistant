"""
Minimal Cortex API Test - No MCP Tools

Simple test to isolate Cortex endpoint issues by:
1. Testing different endpoint URL patterns
2. Removing all MCP tool complexity
3. Making basic API calls to find what works

Run: python test_cortex_minimal.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG to see all SDK activity
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Different Cortex endpoint patterns to test
ENDPOINT_PATTERNS = [
    "/api/v2/cortex/anthropic",  # Try anthropic-specific endpoint
    "/api/v2/cortex/inference:complete",  # CORRECT endpoint from Snowflake docs
    "/api/v2/cortex/complete",
    "/api/v2/cortex/inference/complete",
    "/api/v2/complete",
    "/api/v2/anthropic/complete",
    "/api/v2/cortex/v1/completions",
    "/cortex/v1/completions",
]


async def test_cortex_endpoint(endpoint_path: str) -> bool:
    """
    Test a single Cortex endpoint pattern.

    Args:
        endpoint_path: The URL path to test (e.g. /api/v2/cortex/complete)

    Returns:
        True if endpoint works, False otherwise
    """
    # Get credentials
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if not snowflake_account or not snowflake_password:
        raise ValueError("SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD must be set")

    # Use account name as-is (keep hyphens, lowercase for URL)
    account_for_url = snowflake_account.lower()
    cortex_base_url = f"https://{account_for_url}.snowflakecomputing.com{endpoint_path}"

    print(f"\n{'=' * 70}")
    print(f"Testing endpoint: {cortex_base_url}")
    print(f"{'=' * 70}")

    try:
        # Configure for this endpoint
        os.environ["ANTHROPIC_BASE_URL"] = cortex_base_url
        os.environ["ANTHROPIC_AUTH_TOKEN"] = snowflake_password
        os.environ["ANTHROPIC_MODEL"] = "claude-sonnet-4-5"

        # Create minimal client - NO MCP TOOLS
        options = ClaudeAgentOptions(
            model="claude-sonnet-4-5",
            mcp_servers={},  # Empty - no tools!
            allowed_tools=[],  # No tools allowed
            system_prompt="You are a helpful assistant.",
            max_turns=3,
        )

        # Create client and test
        async with ClaudeSDKClient(options=options) as client:
            logger.info("Client created, sending test query...")

            # Simple test query
            await client.query("Say 'Hello, Cortex works!' and nothing else.")

            # Collect response
            response_parts = []
            async for message in client.receive_response():
                logger.info(f"Received message: {message}")
                if hasattr(message, "content"):
                    response_parts.append(str(message.content))

            full_response = " ".join(response_parts)

            if "Hello" in full_response or "Cortex" in full_response:
                print("\n✓ SUCCESS! This endpoint works!")
                print(f"Response: {full_response[:200]}")
                return True
            else:
                print(f"\n⚠ Unexpected response: {full_response[:200]}")
                return False

    except Exception as e:
        error_msg = str(e)
        print(f"\n✗ FAILED: {error_msg[:300]}")

        # Helpful error categorization
        if "404" in error_msg:
            print("   → 404 Not Found - This endpoint doesn't exist")
        elif "401" in error_msg or "403" in error_msg:
            print("   → Authentication error - Check credentials")
        elif "Connection" in error_msg:
            print("   → Network error - Check connectivity")
        else:
            print("   → Other error type")

        logger.debug(f"Full error: {e}", exc_info=True)
        return False


async def test_all_endpoints():
    """Test all endpoint patterns to find the right one."""
    print("=" * 70)
    print("MINIMAL CORTEX API TEST")
    print("=" * 70)
    print(f"\nAccount: {os.getenv('SNOWFLAKE_ACCOUNT')}")
    print(f"Testing {len(ENDPOINT_PATTERNS)} different endpoint patterns...\n")

    successful_endpoints = []

    for pattern in ENDPOINT_PATTERNS:
        try:
            success = await test_cortex_endpoint(pattern)
            if success:
                successful_endpoints.append(pattern)
        except Exception as e:
            logger.error(f"Fatal error testing {pattern}: {e}")
            continue

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    if successful_endpoints:
        print(f"\n✓ Found {len(successful_endpoints)} working endpoint(s):")
        for endpoint in successful_endpoints:
            print(f"  - {endpoint}")
    else:
        print("\n✗ No working endpoints found!")
        print("\nTroubleshooting:")
        print("  1. Verify SNOWFLAKE_ACCOUNT is correct in .env")
        print("  2. Verify SNOWFLAKE_PASSWORD is correct in .env")
        print("  3. Check if Cortex is enabled in your Snowflake account")
        print("  4. Try accessing Snowflake Cortex through the web UI")
        print("  5. Check Snowflake documentation for the correct API endpoint")


async def quick_test():
    """Quick single endpoint test - modify this to test specific URLs."""
    # Test just the anthropic endpoint quickly
    test_url = "/api/v2/cortex/anthropic"
    print(f"Quick test of: {test_url}\n")
    await test_cortex_endpoint(test_url)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test mode
        asyncio.run(quick_test())
    else:
        # Test all endpoints
        asyncio.run(test_all_endpoints())
