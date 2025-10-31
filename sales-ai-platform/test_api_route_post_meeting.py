#!/usr/bin/env python3
"""
Test script for the post-meeting route in app.py

This script starts the FastAPI server and tests the /post-meeting endpoint
with various call transcripts.

Usage:
    python test_post_meeting.py
"""

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


def test_post_meeting_endpoint(call_transcript: str) -> Optional[dict]:
    """Test the post-meeting endpoint with a given call transcript."""
    url = "http://localhost:8000/post-meeting"
    payload = {"call_transcript": call_transcript}

    try:
        print(f"\n📤 Testing call transcript ({len(call_transcript)} characters)")
        print(f"📝 Preview: {call_transcript[:100]}{'...' if len(call_transcript) > 100 else ''}")
        response = requests.post(url, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            print("📥 Response received:")
            if isinstance(result.get('analysis'), dict):
                print(f"🔍 Analysis keys: {list(result['analysis'].keys())}")
                # Print a sample of the analysis
                for key, value in list(result['analysis'].items())[:3]:
                    if isinstance(value, str):
                        preview = value[:100] + "..." if len(str(value)) > 100 else str(value)
                        print(f"   {key}: {preview}")
                    else:
                        print(f"   {key}: {type(value).__name__}")
            else:
                print(f"   Analysis: {result.get('analysis', 'No analysis found')}")
            return result
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None


def main():
    """Main test function."""
    print("📞 Post-Meeting Route Tester")
    print("=" * 50)

    # Test transcripts
    test_transcripts = [
        """SPEAKER 1: Hi Sarah, thanks for taking the time to meet with us today. I'm John from TechCorp and this is my colleague Mike from the sales team.

SPEAKER 2: Hi John, hi Mike. Great to meet you both. I'm Sarah, the IT Director here at GlobalRetail.

SPEAKER 1: Perfect. So as we discussed in our emails, we're here to talk about how our cloud infrastructure solutions can help streamline your operations and reduce costs.

SPEAKER 2: Yes, that's right. We're currently spending about $50,000 per month on our current setup and we're looking for ways to optimize that.

SPEAKER 1: I see. And what are the main pain points you're experiencing with your current infrastructure?

SPEAKER 2: Well, we have frequent downtime issues, especially during peak shopping seasons. Last Black Friday, we were down for almost 6 hours which cost us significantly in lost sales.

SPEAKER 1: That's definitely something we can help with. Our solution includes 99.9% uptime guarantee and automatic scaling during traffic spikes.

SPEAKER 2: That sounds promising. What would be the next steps if we decide to move forward?

SPEAKER 1: We'd start with a technical assessment of your current setup, then provide a detailed migration plan. The whole process typically takes 6-8 weeks.

SPEAKER 2: Okay, I'll need to discuss this with my team and get budget approval. Can you send me a proposal by next Friday?

SPEAKER 1: Absolutely, I'll have that to you by Thursday. Thanks for your time today, Sarah.""",

        """SPEAKER 1: Good morning, this is Alex from DataSolutions calling about the analytics platform demo we scheduled.

SPEAKER 2: Hi Alex, yes I'm ready. This is Jennifer, the VP of Marketing at StartupXYZ.

SPEAKER 1: Great! So I understand you're looking for better insights into your customer behavior and campaign performance?

SPEAKER 2: Exactly. We're currently using Google Analytics but it's not giving us the depth of insights we need. We need something that can track the full customer journey from first touch to purchase.

SPEAKER 1: Perfect, that's exactly what our platform does. Let me share my screen and show you how it works.

SPEAKER 2: Sounds good.

SPEAKER 1: So as you can see here, we track every touchpoint and can show you attribution across all your marketing channels. This dashboard shows your ROI for each campaign in real-time.

SPEAKER 2: Wow, this is impressive. What's the pricing structure?

SPEAKER 1: We have different tiers starting at $500 per month for up to 10,000 monthly visitors, scaling up from there based on volume.

SPEAKER 2: That fits within our budget. When could we get started?

SPEAKER 1: We could have you set up within a week. I'll send over the contract and implementation timeline today.

SPEAKER 2: Perfect, I look forward to reviewing it."""
    ]

    server_process = None
    try:
        # Start the server
        server_process = start_server()

        # Run tests
        print(f"\n🧪 Running {len(test_transcripts)} test transcripts...")
        successful_tests = 0

        for i, transcript in enumerate(test_transcripts, 1):
            print(f"\n--- Test {i}/{len(test_transcripts)} ---")
            result = test_post_meeting_endpoint(transcript)
            if result:
                successful_tests += 1

        # Summary
        print("\n📊 Test Summary")
        print("=" * 30)
        print(f"✅ Successful: {successful_tests}/{len(test_transcripts)}")
        print(f"❌ Failed: {len(test_transcripts) - successful_tests}/{len(test_transcripts)}")

        if successful_tests == len(test_transcripts):
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