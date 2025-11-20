"""
Direct HTTP Test for Snowflake Cortex API

This test bypasses the Claude Agent SDK entirely and makes raw HTTP requests
to the Cortex API following the exact format from Snowflake documentation.

This helps determine if the issue is:
1. The Claude Agent SDK's handling of Cortex endpoints
2. OR actual Cortex access/configuration issues

Run: uv run test_cortex_direct_http.py
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_cortex_direct_http():
    """
    Make a direct HTTP POST request to Cortex API using requests library.

    This follows the exact format from Snowflake Cortex documentation:
    - POST to /api/v2/cortex/inference:complete
    - Bearer token authentication
    - messages array with role/content
    """
    # Get credentials
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if not snowflake_account or not snowflake_password:
        print("❌ Error: SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD must be set in .env")
        return

    # Use account name AS-IS for hostname (keep hyphens, convert to lowercase)
    # The hostname format is: <account>.snowflakecomputing.com
    account_for_url = snowflake_account.lower()

    # Construct URL with the CORRECT endpoint from Snowflake docs
    url = f"https://{account_for_url}.snowflakecomputing.com/api/v2/cortex/inference:complete"

    print("=" * 70)
    print("DIRECT HTTP TEST - Snowflake Cortex API")
    print("=" * 70)
    print(f"\nAccount: {snowflake_account}")
    print(f"URL: {url}")
    print("\nMaking direct HTTP POST request...\n")

    # Prepare request following Snowflake Cortex documentation format
    headers = {
        "Authorization": f"Bearer {snowflake_password}",
        "Content-Type": "application/json",
    }

    # Request body in the format from Snowflake docs
    data = {
        "model": "claude-sonnet-4-5",
        "messages": [
            {"role": "user", "content": "Say 'Hello from Cortex!' and nothing else."}
        ],
        "max_tokens": 100,
    }

    try:
        # Make the request
        print("Request Headers:")
        print(f"  Authorization: Bearer {snowflake_password[:10]}...")
        print(f"  Content-Type: {headers['Content-Type']}")
        print("\nRequest Body:")
        print(json.dumps(data, indent=2))
        print("\n" + "-" * 70)

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30,
        )

        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("\nResponse Body:")

        # Try to parse as JSON
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))

            # Check if successful
            if response.status_code == 200:
                print("\n" + "=" * 70)
                print("✅ SUCCESS! Cortex API is working!")
                print("=" * 70)

                # Extract the message
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    message = response_json["choices"][0].get("message", {})
                    content = message.get("content", "")
                    print(f"\nCortex Response: {content}")

                return True
            else:
                print("\n" + "=" * 70)
                print(f"❌ FAILED: HTTP {response.status_code}")
                print("=" * 70)
                return False

        except json.JSONDecodeError:
            # Not JSON, print as text
            response_text = response.text[:1000]  # Limit output
            print(response_text)

            if response.status_code == 404:
                print("\n" + "=" * 70)
                print("❌ 404 NOT FOUND")
                print("=" * 70)
                print("\nThis means:")
                print("  1. The endpoint doesn't exist at this URL")
                print("  2. OR Cortex is not enabled on this Snowflake account")
                print("  3. OR the account identifier format is wrong")
                print("\nTroubleshooting:")
                print(f"  - Verify account name: {snowflake_account}")
                print("  - Check if Cortex is enabled in Snowflake web UI")
                print("  - Try logging into Snowflake web console and enabling Cortex")

            return False

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        print("\nThis indicates a network/connection issue.")
        return False


def test_alternative_endpoints():
    """
    Test alternative endpoint formats in case the documentation is wrong.
    """
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if not snowflake_account or not snowflake_password:
        return

    account_for_url = snowflake_account.lower()

    # Alternative endpoints to try
    alternatives = [
        "/api/v2/cortex/inference:complete",  # From docs
        "/api/v2/cortex/complete",  # Without inference prefix
        "/api/v2/inference:complete",  # Without cortex prefix
        "/cortex/inference:complete",  # Without api/v2
    ]

    print("\n\n" + "=" * 70)
    print("TESTING ALTERNATIVE ENDPOINTS")
    print("=" * 70)

    headers = {
        "Authorization": f"Bearer {snowflake_password}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "claude-sonnet-4-5",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 50,
    }

    for endpoint in alternatives:
        url = f"https://{account_for_url}.snowflakecomputing.com{endpoint}"
        print(f"\nTrying: {endpoint}")

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            print(f"  Status: {response.status_code}")

            if response.status_code == 200:
                print(f"  ✅ SUCCESS! Working endpoint: {endpoint}")
                return endpoint
            elif response.status_code == 404:
                print("  ❌ 404 Not Found")
            else:
                print(f"  ⚠️  Got {response.status_code}: {response.text[:100]}")

        except Exception as e:
            print(f"  ❌ Error: {str(e)[:100]}")

    print("\n❌ No working endpoints found")
    return None


if __name__ == "__main__":
    # First test the documented endpoint
    success = test_cortex_direct_http()

    # If that fails, try alternatives
    if not success:
        test_alternative_endpoints()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
