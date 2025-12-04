import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from openai import OpenAI
from pydantic import BaseModel, Field

from graphs.graph_utils import get_llm
from graphs.prompts import HUMAN_MESSAGE_EVAL_USE_CASE_SUMMARY, SYSTEM_PROMPT_EVAL_USE_CASE_SUMMARY

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
