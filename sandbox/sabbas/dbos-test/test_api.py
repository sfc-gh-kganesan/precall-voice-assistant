#!/usr/bin/env python3
"""
Simple test script to demonstrate the DBOS queue API
Run this after starting the FastAPI server with: python main.py
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"


def print_response(title: str, response: requests.Response):
    """Pretty print API responses"""
    print(f"\n{'='*60}")
    print(f"🔹 {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))


def main():
    print("\n🚀 Testing DBOS FastAPI Queue Example\n")
    
    # 1. Test Hello World
    print("1️⃣ Testing Hello World endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print_response("Hello World", response)
    
    # 2. Test Health Check
    print("\n2️⃣ Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", response)
    
    # 3. Enqueue a task
    print("\n3️⃣ Enqueuing a task...")
    task_id = f"task-{int(time.time())}"
    task_data = "hello from test script"
    
    response = requests.post(
        f"{BASE_URL}/queue/enqueue",
        params={
            "task_id": task_id,
            "task_data": task_data
        }
    )
    print_response("Enqueue Task", response)
    
    # Get workflow ID
    workflow_id = response.json().get("workflow_id")
    
    if workflow_id:
        # 4. Check workflow status (immediately)
        print("\n4️⃣ Checking workflow status (immediate - should be PENDING)...")
        response = requests.get(f"{BASE_URL}/queue/status/{workflow_id}")
        print_response("Workflow Status (immediate)", response)
        
        # 5. Poll for completion
        print("\n⏳ Polling for completion (workflow takes ~5 seconds)...")
        max_attempts = 15
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(1)
            attempt += 1
            response = requests.get(f"{BASE_URL}/queue/status/{workflow_id}")
            status = response.json().get("status")
            print(f"   Attempt {attempt}: Status = {status}")
            
            if status == "SUCCESS":
                print("   ✅ Workflow completed!")
                break
        
        print("\n5️⃣ Final workflow result...")
        response = requests.get(f"{BASE_URL}/queue/status/{workflow_id}")
        print_response("Workflow Status (final)", response)
    
    # 6. Enqueue multiple tasks
    print("\n6️⃣ Enqueuing multiple tasks...")
    workflow_ids = []
    for i in range(3):
        task_id = f"batch-task-{i}"
        task_data = f"batch data {i}"
        
        response = requests.post(
            f"{BASE_URL}/queue/enqueue",
            params={
                "task_id": task_id,
                "task_data": task_data
            }
        )
        
        wf_id = response.json().get("workflow_id")
        workflow_ids.append(wf_id)
        print(f"  ✓ Enqueued {task_id} -> {wf_id}")
    
    # Wait for batch to complete
    print("\n⏳ Waiting for batch to complete (this will take ~5 seconds)...")
    time.sleep(6)
    
    # Check all statuses
    print("\n7️⃣ Checking batch results...")
    for wf_id in workflow_ids:
        response = requests.get(f"{BASE_URL}/queue/status/{wf_id}")
        result = response.json()
        print(f"  Workflow {wf_id[:20]}... -> {result.get('status')}")
        if result.get('result'):
            print(f"    Result: {result['result'].get('result')}")
    
    # 8. Check scheduled workflows
    print("\n8️⃣ Checking scheduled workflow count...")
    print("   (Scheduled workflow runs every 30 seconds in the background)")
    print("")
    
    response = requests.get(f"{BASE_URL}/scheduled/count")
    print_response("Scheduled Workflow Count", response)
    
    print("\n💡 Tip: Keep the server running and check this endpoint again")
    print("   in 30 seconds to see the count increase!")
    print(f"   curl {BASE_URL}/scheduled/count")
    
    print("\n✅ All tests completed!")
    print("\n" + "="*60)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the API server.")
        print("   Make sure the server is running: python main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")

