import argparse
import asyncio
import csv
import os
import tempfile
from pathlib import Path
from typing import Iterable

from langsmith import Client
from openevals.llm import create_llm_as_judge

from app.graph import run_workflow
from app.utils import run_query
from evals.prompt import JUDGE_PROMPT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run LangSmith evaluations using a CSV file or a Snowflake table."
    )
    parser.add_argument(
        "--eval-csv-file",
        type=Path,
        help="Path to a CSV file containing evaluation data.",
    )
    parser.add_argument(
        "--eval-snowflake-table",
        type=str,
        default=os.getenv("EVALS_SNOWFLAKE_TABLE"),
        help="Fully qualified Snowflake table name providing evaluation data.",
    )
    parser.add_argument(
        "--evals-table",
        type=str,
        default=os.getenv("EVALS_TABLE"),
        help="Fallback evaluation table value if dataset rows omit it.",
    )
    parser.add_argument(
        "--eval-stage-name",
        type=str,
        default=os.getenv("EVALS_STAGE_NAME"),
        help="Fallback evaluation stage_name value if dataset rows omit it.",
    )
    return parser.parse_args()


args = parse_args()
client = Client()

DEFAULT_TARGET_TABLE = args.target_table
DEFAULT_STAGE_NAME = args.stage_name

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

columns: list[str] = input_keys + output_keys


def ensure_value(row: dict, key: str, fallback: str | None = None) -> str | None:
    value = row.get(key) or row.get(key.upper()) or row.get(key.lower())
    return value or fallback


cleanup_csv = False

if args.snowflake_table:
    snowflake_rows = run_query("SELECT * FROM identifier(%(table)s)", {"table": args.snowflake_table})
    if isinstance(snowflake_rows, str):
        raise RuntimeError(f"Failed to load evaluation data from Snowflake: {snowflake_rows}")

    with tempfile.NamedTemporaryFile("w", newline="", suffix=".csv", delete=False) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=columns)
        writer.writeheader()
        for row in snowflake_rows:
            record = {col: ensure_value(row, col) for col in columns}
            if not record["target_table"]:
                record["target_table"] = DEFAULT_TARGET_TABLE
            if not record["stage_name"]:
                record["stage_name"] = DEFAULT_STAGE_NAME
            if not record["target_table"] or not record["stage_name"]:
                raise ValueError(
                    "Each evaluation row must include target_table and stage_name "
                    "or provide defaults with --target-table/--stage-name."
                )
            writer.writerow(record)
        csv_file = tmp.name
        cleanup_csv = True
else:
    csv_path = args.csv_file or Path("evals/data/test_set.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found at {csv_path}")
    csv_file = str(csv_path)


dataset_name = "SDK Test Dataset"

try:
    client.delete_dataset(dataset_name=dataset_name)
    print(f"Dataset '{dataset_name}' deleted successfully.")
except Exception as exc:
    print(f"Could not delete dataset '{dataset_name}': {exc}")


dataset = client.upload_csv(
  csv_file=csv_file,
  input_keys=input_keys,
  output_keys=output_keys,
  name=dataset_name,
  description="Dataset created from a CSV file",
  data_type="kv"
)

if cleanup_csv:
    try:
        os.unlink(csv_file)
    except OSError:
        pass


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
    if DEFAULT_TARGET_TABLE and not inputs.get("target_table"):
        inputs["target_table"] = DEFAULT_TARGET_TABLE
    if DEFAULT_STAGE_NAME and not inputs.get("stage_name"):
        inputs["stage_name"] = DEFAULT_STAGE_NAME
    if not inputs.get("target_table") or not inputs.get("stage_name"):
        raise ValueError(
            "Inputs must include target_table and stage_name. "
            "Provide via dataset columns or --target-table/--stage-name."
        )
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