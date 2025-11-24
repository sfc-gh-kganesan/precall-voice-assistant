#!/usr/bin/env python3
"""
Test client for the DDA Agent API

Demonstrates how to interact with the agent API from another service (like agentsim).
"""

import asyncio
import json

import httpx


API_BASE_URL = "http://localhost:8002"


async def test_health_check():
    """Test the health endpoint"""
    print("\n" + "=" * 70)
    print("Testing Health Check")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")


async def test_list_tools():
    """Test the tools listing endpoint"""
    print("\n" + "=" * 70)
    print("Testing List Tools")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/tools")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")


async def test_simple_query():
    """Test a simple non-streaming query"""
    print("\n" + "=" * 70)
    print("Testing Simple Query (Non-Streaming)")
    print("=" * 70)

    query = "What tools do you have available?"
    print(f"Query: {query}\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/query/simple",
            json={"message": query},
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"\nResponse:\n{result['response']}")


async def test_streaming_query():
    """Test a streaming query with Server-Sent Events"""
    print("\n" + "=" * 70)
    print("Testing Streaming Query (SSE)")
    print("=" * 70)

    query = "Search for documents about authentication"
    print(f"Query: {query}\n")
    print("Streaming response:\n" + "-" * 70)

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{API_BASE_URL}/query",
            json={"message": query, "stream": True},
        ) as response:
            full_text = ""

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = line.split(":", 1)[1].strip()
                    try:
                        data_json = json.loads(data)

                        if event_type == "tool_call":
                            print(f"\n🔧 Calling tool: {data_json['tool']}")
                        elif event_type == "tool_result":
                            print(f"✅ Tool completed: {data_json['tool']}")
                        elif event_type == "text_delta":
                            content = data_json.get("content", "")
                            print(content, end="", flush=True)
                            full_text += content
                        elif event_type == "final":
                            print("\n" + "-" * 70)
                            print("\nFinal response received")
                        elif event_type == "error":
                            print(f"\n❌ Error: {data_json.get('error')}")

                    except json.JSONDecodeError:
                        pass


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("DDA Agent API Test Client")
    print("=" * 70)
    print("\nMake sure the following are running:")
    print("  1. DDA MCP Server (port 8000)")
    print("  2. Glean Proxy (port 8001)")
    print("  3. Agent API (port 8002)")
    print("\nStart with: uv run start_services.py")
    input("\nPress Enter to start tests...")

    try:
        # Run tests
        await test_health_check()
        await asyncio.sleep(1)

        await test_list_tools()
        await asyncio.sleep(1)

        await test_simple_query()
        await asyncio.sleep(1)

        await test_streaming_query()

        print("\n" + "=" * 70)
        print("All tests completed!")
        print("=" * 70)

    except httpx.ConnectError:
        print("\n❌ Connection failed!")
        print("\nMake sure all services are running:")
        print("  uv run start_services.py")
        print("  uv run app/agent_api.py")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
