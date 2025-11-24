#!/usr/bin/env python3
"""
Standalone test script for Cortex Search Service REST API.
Tests both Bearer and Snowflake Token authentication formats.
"""

import asyncio
import json
import os
import sys

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_cortex_search(auth_format: str = "bearer"):
    """
    Test Cortex Search with different auth formats.

    Args:
        auth_format: Either "bearer" or "snowflake_token"
    """
    # Get credentials from environment
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    password = os.getenv("SNOWFLAKE_PASSWORD")

    if not account or not password:
        print("❌ ERROR: SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD must be set")
        sys.exit(1)

    # Service configuration (using the correct values we identified)
    database = "CORTEX_KNOWLEDGE_EXTENSION_SNOWFLAKE_DOCUMENTATION"
    schema = "SHARED"
    service_name = "CKE_SNOWFLAKE_DOCS_SERVICE"

    # Construct URL
    service_url = (
        f"https://{account}.snowflakecomputing.com/api/v2/databases/{database}/schemas/{schema}"
        f"/cortex-search-services/{service_name}:query"
    )

    # Test query
    query = "CREATE TABLE syntax"

    # Payload
    payload = {
        "query": query,
        "columns": ["CHUNK"],
        "scoring_config": {
            "weights": {
                "texts": 1,
                "vectors": 1,
                "reranker": 1,
            },
        },
        "limit": 3,
    }

    # Set up headers based on auth format
    if auth_format == "bearer":
        auth_header = f"Bearer {password}"
    else:  # snowflake_token
        auth_header = f'Snowflake Token="{password}"'

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": auth_header,
    }

    # Print test details
    print(f"\n{'=' * 80}")
    print(f"Testing Cortex Search with {auth_format.upper()} authentication")
    print(f"{'=' * 80}")
    print(f"\n📍 URL: {service_url}")
    print(f"\n🔑 Auth Header: Authorization: {auth_header[:50]}...")
    print(f"\n📝 Query: {query}")
    print("\n📦 Payload:")
    print(json.dumps(payload, indent=2))

    # Make the request
    print("\n🚀 Sending request...")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                service_url,
                json=payload,
                headers=headers,
            )

            # Print response details
            print(f"\n✅ Response Status: {response.status_code}")
            print("\n📨 Response Headers:")
            for key, value in response.headers.items():
                if key.lower() not in ["set-cookie", "authorization"]:
                    print(f"  {key}: {value}")

            print("\n📄 Response Body:")
            try:
                response_json = response.json()
                print(json.dumps(response_json, indent=2))

                # If successful, show results
                if response.status_code == 200:
                    results = response_json.get("results", [])
                    print(f"\n✨ Found {len(results)} results!")
                    for idx, result in enumerate(results, 1):
                        chunk = result.get("CHUNK", "")
                        print(f"\n--- Result {idx} ---")
                        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
                else:
                    print(f"\n❌ Request failed with status {response.status_code}")

            except json.JSONDecodeError:
                print(response.text)

            # Raise for status to trigger error handling
            response.raise_for_status()

            return True

        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error: {e.response.status_code}")
            print(f"Response: {e.response.text}")
            return False

        except httpx.RequestError as e:
            print(f"\n❌ Request Error: {e}")
            return False

        except Exception as e:
            print(f"\n❌ Unexpected Error: {e}")
            return False


async def main():
    """Run tests with both auth formats."""
    print("\n" + "=" * 80)
    print("CORTEX SEARCH SERVICE TEST")
    print("=" * 80)

    # Test 1: Bearer token (from official docs)
    print("\n\n🧪 TEST 1: Bearer Token Authentication")
    bearer_success = await test_cortex_search("bearer")

    # Test 2: Snowflake Token (alternative format found in codebase)
    print("\n\n🧪 TEST 2: Snowflake Token Authentication")
    snowflake_token_success = await test_cortex_search("snowflake_token")

    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Bearer Token: {'✅ SUCCESS' if bearer_success else '❌ FAILED'}")
    print(
        f"Snowflake Token: {'✅ SUCCESS' if snowflake_token_success else '❌ FAILED'}"
    )
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
