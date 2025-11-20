#!/usr/bin/env python3
"""
Script to run the post-meeting workflow graph for testing purposes.

This script will invoke the post-meeting workflow with test data from the synthetic table
when DEMO_MODE=true is set in the environment.
"""

import asyncio
import os

from dotenv import load_dotenv

from graphs.post_meeting_workflow import graph

load_dotenv()


# Input records from synthetic table
inputs_records = [
    {"activity_id": "7578ghohjgt8rthljmvotur87947597935", "owner_id": "004G0005867qtHRAN", "salesforce_account_id": "00184759847rG98TAU78"},
    {"activity_id": "9chdhagbdhajj5jlj95584unajgljfdg94u858", "owner_id": "004G0005867qtHRAN", "salesforce_account_id": "00184759847rG98TAU78"},
    {"activity_id": "890uhjdklg9898t890fjkdjalgjjh88r88t8882223", "owner_id": "004G0005867qtHRAN", "salesforce_account_id": "00184759847rG98TAU78"},
    {"activity_id": "12345969808jhgqpeuruzvn58t8ty7r8invat887", "owner_id": "00789BNV8ouWWH", "salesforce_account_id": "002YTN87708FJbrdsd342"},
]


async def run_workflow_async(test_inputs: list[dict]):
    """Run the workflow asynchronously."""

    print("Starting Post-Meeting Workflow Test")
    print(f"DEMO_MODE = {os.getenv('DEMO_MODE', 'false')}")
    print("-" * 50)

    for i, test_input in enumerate(test_inputs, 1):
        print(f"\nTest Case {i}:")
        print(f"   Activity ID: {test_input['activity_id']}")
        print(f"   Account ID: {test_input['salesforce_account_id']}")
        print(f"   Owner ID: {test_input['owner_id']}")

        try:
            # Invoke the workflow graph
            result = await graph.ainvoke(test_input)

            print("Workflow completed successfully! \n")
            print("Full result:")
            print(result)

        except Exception as e:
            print(f"Workflow failed: {str(e)}")
            print(f"   Error type: {type(e).__name__}")

        print("-" * 50)


def run_workflow_sync(test_inputs: list[dict]):
    """Run the workflow synchronously."""

    # Test input data - these should exist in your synthetic table
    test_input = test_inputs[0]

    print("Starting Post-Meeting Workflow Test (Sync)")
    print(f"DEMO_MODE = {os.getenv('DEMO_MODE', 'false')}")
    print("-" * 50)

    print("Test Input:")
    print(f"   Activity ID: {test_input['activity_id']}")
    print(f"   Account ID: {test_input['salesforce_account_id']}")
    print(f"   Owner ID: {test_input['owner_id']}")

    try:
        # Invoke the workflow graph synchronously
        result = graph.invoke(test_input)

        print("Workflow completed successfully! \n")
        print("Full result:")
        print(result)

    except Exception as e:
        print(f"Workflow failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback

        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    print("Post-Meeting Workflow Test Runner (NOTE: Must have DEMO_MODE=true in your .env file)")
    print("=" * 50)

    if os.getenv("DEMO_MODE", "false").lower() != "true":
        print("WARNING: DEMO_MODE is not enabled!")
        print("   Set DEMO_MODE=true in your .env file to use synthetic data")
    else:
        # Allow user to choose sync or async
        mode = input("\nChoose execution mode:\n1. Sync (s)\n2. Async (a)\nEnter choice [s/a]: ").lower().strip()

        if mode in ["a", "async", "2"]:
            print("\nRunning in async mode...")
            asyncio.run(run_workflow_async(inputs_records))
        else:
            print("\nRunning in sync mode...")
            run_workflow_sync(inputs_records)

        print("\nTest completed!")
