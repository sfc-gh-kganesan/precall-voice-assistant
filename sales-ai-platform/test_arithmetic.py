#!/usr/bin/env python3
"""
Test script for the arithmetic route in app.py

This script starts the FastAPI server and tests the /arithmetic endpoint
with various arithmetic queries.

Usage:
    python test_arithmetic.py
"""

import asyncio
import subprocess
import time
import sys
import requests
from typing import Optional


def start_server() -> subprocess.Popen:
    """Start the FastAPI server in a subprocess."""
    print("🚀 Starting FastAPI server...")
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd="/Users/kmason/Documents/FDE/GitHub/aura/sales-ai-platform",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Wait for server to start up
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/", timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return process
        except requests.exceptions.RequestException:
            if attempt < max_attempts - 1:
                print(f"⏳ Waiting for server... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(2)
            else:
                print("❌ Server failed to start")
                process.terminate()
                raise

    return process


def test_arithmetic_endpoint(query: str) -> Optional[dict]:
    """Test the arithmetic endpoint with a given query."""
    url = "http://localhost:8000/arithmetic"
    payload = {"query": query}

    try:
        print(f"\n📤 Testing: '{query}'")
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"📥 Response: {result['answer']}")
            print(f"🔧 Tool calls made: {result['tool_calls_made']}")
            return result
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None


def main():
    """Main test function."""
    print("🧮 Arithmetic Route Tester")
    print("=" * 50)

    # Test queries
    test_queries = [
        "What is 25 + 17?",
        "Multiply 12 by 8, then divide by 3",
    ]

    server_process = None
    try:
        # Start the server
        server_process = start_server()

        # Run tests
        print(f"\n🧪 Running {len(test_queries)} test queries...")
        successful_tests = 0

        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test {i}/{len(test_queries)} ---")
            result = test_arithmetic_endpoint(query)
            if result:
                successful_tests += 1

        # Summary
        print(f"\n📊 Test Summary")
        print("=" * 30)
        print(f"✅ Successful: {successful_tests}/{len(test_queries)}")
        print(f"❌ Failed: {len(test_queries) - successful_tests}/{len(test_queries)}")

        if successful_tests == len(test_queries):
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")

    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
    finally:
        # Clean up server
        if server_process:
            print("\n🔄 Shutting down server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("✅ Server shut down cleanly")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing server...")
                server_process.kill()


if __name__ == "__main__":
    main()