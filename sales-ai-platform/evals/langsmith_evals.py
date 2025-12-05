import asyncio
import os

from dbos import DBOS
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from openai import OpenAI
from pydantic import BaseModel, Field

from evals.prod_logging import build_eval_correctness_results_query, build_eval_insert_query, build_eval_results_lookup_query, build_eval_state_lookup_query
from graphs.graph_utils import get_llm
from graphs.prompts import HUMAN_MESSAGE_EVAL_USE_CASE_SUMMARY, SYSTEM_PROMPT_EVAL_USE_CASE_SUMMARY
from utils import compute_eval_id, execute_snowflake_query_sync

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
eval_model_selection = os.getenv("EVAL_MODEL_SELECTION", "openai-gpt-4.1")


class EvalOutputState(BaseModel):
    accuracy: float = Field(default=0.0, description="Accuracy score")
    groundedness: float = Field(default=0.0, description="Groundedness score")
    completeness: float = Field(default=0.0, description="Completeness score")
    actionability: float = Field(default=0.0, description="Actionability score")


def judge_summary(transcript: str, summary: str) -> dict:
    llm = get_llm(cortex_model_selection=eval_model_selection)

    system_prompt = SystemMessage(content=SYSTEM_PROMPT_EVAL_USE_CASE_SUMMARY)
    human_prompt = HumanMessage(content=HUMAN_MESSAGE_EVAL_USE_CASE_SUMMARY.format(transcript=transcript, summary=summary))

    try:
        response = llm.with_structured_output(EvalOutputState).invoke([system_prompt, human_prompt])
        response_dict = response.model_dump()
        return response_dict
    except Exception as e:
        print(f"Error: Failed to evaluate use case summary: {e}")


@DBOS.step()
async def lookup_eval_scores_from_snowflake(
    eval_id: str,
) -> dict:
    """
    Lookup the evaluation scores from the Snowflake table.
    """
    eval_result_query, eval_state_query = build_eval_results_lookup_query(eval_id), build_eval_state_lookup_query(eval_id)

    eval_result, eval_state = None, None
    try:
        eval_result, eval_state = await asyncio.gather(
            asyncio.to_thread(execute_snowflake_query_sync, eval_result_query),
            asyncio.to_thread(execute_snowflake_query_sync, eval_state_query),
        )
    except Exception as e:
        DBOS.logger.error(f"Failed to lookup evaluation scores from Snowflake for eval_id: {eval_id}: {str(e)}")
        return None

    if eval_result is None or eval_state is None or len(eval_result[0]) == 0:
        return None

    return {
        "eval_result": {k.lower(): v for k, v in eval_result[0][0].as_dict().items()},
        "eval_state": {k.lower(): v for k, v in eval_state[0][0].as_dict().items()},
    }


@DBOS.step()
async def evaluate_use_case_summary_prod(
    salesforce_account_id: str,
    owner_id: str,
    activity_id: str,
    graph_version: str,
    transcript: str,
    summary: str,
) -> dict:
    """
    Evaluate the use case summary and log the results to the Snowflake table.
    """
    eval_id = compute_eval_id(activity_id, owner_id, salesforce_account_id, graph_version)

    # Step 3: Execute the evaluation logging query for the generated use case summaries
    scores = None
    eval_scoring_error_message = ""
    try:
        scores = judge_summary(transcript, summary)
    except Exception as e:
        DBOS.logger.error(f"Failed to evaluate use case summary for activity_id: {activity_id}: {str(e)}")
        eval_scoring_error_message = str(e)

    # Step 4: Compose the evaluation logging query and insert the scores into the Snowflake table
    eval_query = build_eval_insert_query(eval_id, salesforce_account_id, owner_id, activity_id, graph_version, scores)
    eval_results, eval_query_id = None, None
    eval_insert_error_message = ""
    try:
        eval_results, eval_query_id = await asyncio.to_thread(execute_snowflake_query_sync, eval_query)
    except Exception as e:
        DBOS.logger.error(f"Failed to execute evaluation logging query for activity_id: {activity_id}: {str(e)}")
        eval_insert_error_message = str(e)

    # Step 5: Compose the evaluation correctness logging query and insert the results into the Snowflake table
    eval_correctness_query = build_eval_correctness_results_query(eval_id, graph_version, True, "No error found.", "N/A")
    eval_success, error_stage, eval_message = True, "N/A", "No error found."
    if eval_scoring_error_message != "" or eval_insert_error_message != "":
        eval_success = False
        error_stage = "eval_scoring" if eval_scoring_error_message != "" else "eval_insert"
        eval_message = eval_scoring_error_message if eval_scoring_error_message != "" else eval_insert_error_message
        eval_correctness_query = build_eval_correctness_results_query(eval_id, graph_version, False, eval_message, error_stage)

    try:
        eval_correctness_results, eval_correctness_query_id = await asyncio.to_thread(execute_snowflake_query_sync, eval_correctness_query)
    except Exception as e:
        DBOS.logger.error(f"Failed to execute evaluation correctness query for activity_id: {activity_id}: {str(e)}")

    return {
        "eval_id": eval_id,
        "scores": scores,
        "error_stage": error_stage,
        "eval_error_message": eval_message,
        "eval_success": eval_success,
    }
