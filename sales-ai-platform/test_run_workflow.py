#!/usr/bin/env python3
"""
Script to run the post-meeting workflow graph for testing purposes.

This script will invoke the post-meeting workflow with test data from the synthetic table
when DEMO_MODE=true is set in the environment.
"""

import asyncio
import os

from dotenv import load_dotenv
from langsmith.run_helpers import trace

from graphs.langsmith_evals import judge_summary
from graphs.post_meeting_workflow import graph
from utils import get_snowflake_session

load_dotenv()

demo_mode = os.getenv("DEMO_MODE", "false").lower()

if demo_mode == "true":
    # Input records from synthetic table
    input_records = [
        {"activity_id": "7578ghohjgt8rthljmvotur87947597935", "owner_id": "004G0005867qtHRAN", "salesforce_account_id": "00184759847rG98TAU78"},
        {"activity_id": "9chdhagbdhajj5jlj95584unajgljfdg94u8585", "owner_id": "004G0005867qtHRAN", "salesforce_account_id": "00184759847rG98TAU78"},
        {"activity_id": "890uhjdklg9898t890fjkdjalgjjh88r88t8882223", "owner_id": "004G0005867qtHRAN", "salesforce_account_id": "00184759847rG98TAU78"},
        {"activity_id": "12345969808jhgqpeuruzvn58t8ty7r8invat887", "owner_id": "00789BNV8ouWWH", "salesforce_account_id": "002YTN87708FJbrdsd342"},
    ]
else:
    session = get_snowflake_session()

    query = """
    select *
    from sales.engagement360_pitch.all_engagement_details
    where TYPE = 'MEETING'
        and RAW_CONTENT is not null
        and OWNER_ID = '005VI00000QLxXZYA1'
        and lower(PARTICIPANT_NAMES) like '%tara%'
        and RAW_CONTENT not like '%## Quick recap%'
    LIMIT 1
    """

    sdf = session.sql(query).collect()
    input_records = [{"activity_id": row["ACTIVITY_ID"], "owner_id": row["OWNER_ID"], "salesforce_account_id": row["SALESFORCE_ACCOUNT_ID"], "transcript": row["RAW_CONTENT"], "takeaways": row["TAKEAWAYS"]} for row in sdf]


async def run_workflow_async(test_inputs: list[dict]):
    """Run the workflow asynchronously."""

    print("Starting Post-Meeting Workflow Test")
    print(f"DEMO_MODE = {demo_mode}")
    print("-" * 50)

    for i, test_input in enumerate(test_inputs, 1):
        print(f"\nTest Case {i}:")
        print(f"   Activity ID: {test_input['activity_id']}")
        print(f"   Account ID: {test_input['salesforce_account_id']}")
        print(f"   Owner ID: {test_input['owner_id']}")

        try:
            # Invoke the workflow graph
            with trace(name="post_meeting_workflow", run_type="chain") as ls:
                result = await graph.ainvoke(test_input)
                scores = judge_summary(test_input["transcript"], result["new_use_cases"])
                ls.metadata["eval_scores"] = scores
                ls.tags.append(f"acc:{scores['accuracy']:.2f}")
                ls.tags.append(f"gnd:{scores['groundedness']:.2f}")
                ls.tags.append(f"cmp:{scores['completeness']:.2f}")
                ls.tags.append(f"act:{scores['actionability']:.2f}")

                print("Workflow completed successfully! \n")
                print("Full result:")
                print(result)
                print("Evaluation scores:")
                print(scores)

                with trace(name="eval_judge", run_type="llm") as eval_run:
                    eval_run.inputs["transcript"] = test_input["transcript"]
                    eval_run.inputs["use_cases"] = result["new_use_cases"]
                    eval_run.outputs["scores"] = scores

        except Exception as e:
            print(f"Workflow failed: {str(e)}")
            print(f"   Error type: {type(e).__name__}")

        print("-" * 50)


def run_workflow_sync(test_inputs: list[dict]):
    """Run the workflow synchronously."""

    # Test input data - only use a single input record for sync mode
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
    print("Post-Meeting Workflow Test Runner")
    print("=" * 50)

    # if demo_mode != "true":
    #     print("WARNING: DEMO_MODE is not enabled!")
    #     print("   Set DEMO_MODE=true in your .env file to use synthetic data")
    # else:
    #     # Allow user to choose sync or async
    #     mode = input("\nChoose execution mode:\n1. Sync (s)\n2. Async (a)\nEnter choice [s/a]: ").lower().strip()

    #     if mode in ["a", "async", "2"]:
    #         print("\nRunning in async mode...")
    #         asyncio.run(run_workflow_async(input_records))
    #     else:
    #         print("\nRunning in sync mode...")
    #         run_workflow_sync(input_records)

    #     print("\nTest completed!")

    # Allow user to choose sync or async
    mode = input("\nChoose execution mode:\n1. Sync (s)\n2. Async (a)\nEnter choice [s/a]: ").lower().strip()

    if mode in ["a", "async", "2"]:
        print("\nRunning in async mode...")
        asyncio.run(run_workflow_async(input_records))
    else:
        print("\nRunning in sync mode...")
        run_workflow_sync(input_records)

    print("\nTest completed!")
