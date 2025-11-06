import asyncio
from langsmith import Client
from openevals.llm import create_llm_as_judge

from app.graph import run_workflow
from evals.prompt import JUDGE_PROMPT


client = Client()

csv_file = 'evals/data/test_set.csv'
dataset_name = 'SDK Test Dataset'

try:
    # Attempt to delete the dataset by name
    client.delete_dataset(dataset_name=dataset_name)
    print(f"Dataset '{dataset_name}' deleted successfully.")
except Exception as e:
    # Handle the case where the dataset might not exist or other errors occur
    print(f"Could not delete dataset '{dataset_name}': {e}")

input_keys = [
    'target_table',
    'invoice_id',
    'relative_path',
    'stage_name'
    ] 
# Ground truth columns go into output_keys here
output_keys = [
    'company_name',
    'purchase_order_number',
    'payment_terms',
    'vendor_name',
    'invoice_date',
    'currency',
    'total_amount',
    'tax_amount',
    'memo_description',
    'expected_decision'
]

dataset = client.upload_csv(
  csv_file=csv_file,
  input_keys=input_keys,
  output_keys=output_keys,
  name=dataset_name,
  description="Dataset created from a CSV file",
  data_type="kv"
)

correctness_evaluator = create_llm_as_judge(
    prompt=JUDGE_PROMPT,
    feedback_key="extract_correctness",
    model="openai:o3-mini",
    choices = [0, 1],
)

def wrapped_correctness_evaluator(
    inputs: dict,
    outputs: dict,
    reference_outputs: dict,
):
    eval_result = correctness_evaluator(
        inputs=inputs,
        outputs=outputs,
        reference_outputs=reference_outputs,
    )
    return eval_result


async def wrapped_graph_target(inputs: dict) -> dict:
    return await run_workflow(**inputs)

async def main():
    results = await client.aevaluate(
        wrapped_graph_target,
        data=dataset.name,
        evaluators=[wrapped_correctness_evaluator],
        experiment_prefix="sdk_test",  # optional, experiment name prefix
        description="Testing the SDK for evals",  # optional, experiment description
        max_concurrency=1, # optional, add concurrency
    )
    return results

if __name__ == "__main__":
    results = asyncio.run(main())
    print(results)