"""
Post Meeting Workflow Graph

This workflow processes a call transcipt to extract specific information.
"""

import os

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from graphs.graph_utils import get_llm
from graphs.prompts import HUMAN_MESSAGE_USE_CASE_EXTRACTION, SYSTEM_PROMPT_USE_CASE_EXTRACTION
from utils import get_snowflake_session

# import json
# from typing import Annotated


# # Define State Schemas
# class OverallState(TypedDict):
#     activity_id: str
#     salesforce_account_id: str
#     owner_id: str
#     call_transcript: str
#     takeaways: str
#     next_steps: list[str]
#     opportunity_comments: list[str]
#     deal_stage: str
#     close_date: str
#     opportunity_meddpicc_status: str
#     new_use_cases: list[str]
#     objections: list[str]


# class SFDCOutputState(BaseModel):
#     next_steps: list[str] = Field(default_factory=list, description="List of next steps from the call")
#     close_date: str = Field(default="", description="Expected close date (YYYY-MM-DD)")
#     new_use_cases: list[str] = Field(default_factory=list, description="List of new use cases identified")
#     objections: list[str] = Field(default_factory=list, description="List of customer objections and issues that were raised")
#     opportunity_comments: list[str] = Field(default_factory=list, description="List of opportunity comments")


# class OutputState(TypedDict):
#     next_steps: list[str]
#     opportunity_comments: list[str]
#     close_date: str
#     new_use_cases: list[str]
#     objections: list[str]


# Define State Schemas


# Pydantic model for a single use case
class UseCaseItem(BaseModel):
    use_case_description: str = Field(default="", description="Description of the use case")
    use_case_name: str = Field(default="", description="Name of the use case")
    workloads: list[str] = Field(default_factory=list, description="List of workloads the use case could be classified as")
    technical_use_cases: list[str] = Field(default_factory=list, description="List of technical use cases the use case could be classified as")
    incumbent_vendor: str = Field(default="", description="Existing vendor/tool/platform that customer is already using or considering using to solve the use case")


# Overall State
class OverallState(BaseModel):
    activity_id: str = Field(default="", description="Activity ID")
    salesforce_account_id: str = Field(default="", description="Salesforce Account ID")
    owner_id: str = Field(default="", description="Owner ID")
    call_transcript: str = Field(default="", description="Call transcript")
    takeaways: str = Field(default="", description="Takeaways")
    new_use_cases: list[UseCaseItem] = Field(default_factory=list, description="List of new use cases identified.")


# Pydantic model for the structured output of the use case extraction
class SFDCUseCasesOutputState(BaseModel):
    new_use_cases: list[UseCaseItem] = Field(default_factory=list, description="List of new use cases identified. (Leave empty if no use cases were discussed)")


# Final output state of the entire graph
class OutputState(BaseModel):
    new_use_cases: list[UseCaseItem] = Field(default_factory=list, description="List of new use cases identified")


# Create nodes
def extract_transcript(state: OverallState) -> OverallState:
    """
    Extract the call transcript from snowflake table
    """

    session = get_snowflake_session()

    # Use synthetic data table for demo mode, otherwise use production table
    table_name = "ai_fde.sales_ai_platform.all_engagement_details_synthetic" if os.getenv("DEMO_MODE", "false").lower() == "true" else "sales.engagement360_pitch.all_engagement_details"

    query = f"""
    SELECT RAW_CONTENT, TAKEAWAYS
    FROM {table_name}
    WHERE activity_id = '{state.activity_id}'
    AND salesforce_account_id = '{state.salesforce_account_id}'
    AND owner_id = '{state.owner_id}'
    ORDER BY activity_date desc
    LIMIT 1
    """
    results = session.sql(query).collect()

    if not results:
        raise ValueError(f"No transcript found for activity_id={state.activity_id}, salesforce_account_id={state.salesforce_account_id}, owner_id={state.owner_id}")

    transcript = results[0]["RAW_CONTENT"]
    takeaways = results[0]["TAKEAWAYS"]
    return {"call_transcript": transcript, "takeaways": takeaways}


# def sfdc_assistant(state: OverallState) -> OverallState:
#     """
#     Extract SFDC fields from the call transcript.
#     """
#     llm = get_llm(cortex_model_selection="openai-gpt-4.1")
#     system_prompt = SYSTEM_PROMPT_SFDC_EXTRACTION
#     human_prompt = HUMAN_MESSAGE_SFDC_EXTRACTION.format(transcript=state["call_transcript"])
#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=human_prompt),
#     ]

#     # response = llm.invoke(messages)
#     response = llm.with_structured_output(SFDCOutputState).invoke(messages)

#     # # Format response as JSON (if using a TypedDict state)
#     # try:
#     #     response_dict = json.loads(response.content)
#     # except json.JSONDecodeError:
#     #     response_dict = {"error": "Failed to parse response as JSON"}

#     # response_dict = response # If using structured output with a TypedDict state

#     response_dict = response.model_dump()  # If using structured output with a pydantic BaseModel state

#     return {
#         # "messages": [response],
#         "next_steps": response_dict["next_steps"],
#         "close_date": response_dict["close_date"],
#         "new_use_cases": response_dict["new_use_cases"],
#         "objections": response_dict["objections"],
#         "opportunity_comments": response_dict["opportunity_comments"],
#     }


# def final_results(state: OverallState) -> OutputState:
#     return {
#         "next_steps": state["next_steps"],
#         "close_date": state["close_date"],
#         "new_use_cases": state["new_use_cases"],
#         "objections": state["objections"],
#         "opportunity_comments": state["opportunity_comments"],
#     }


def new_use_case_assistant(state: OverallState) -> OverallState:
    """
    Extract new use cases from the call transcript.
    """
    llm = get_llm(cortex_model_selection="openai-gpt-4.1")
    system_prompt = SYSTEM_PROMPT_USE_CASE_EXTRACTION
    human_prompt = HUMAN_MESSAGE_USE_CASE_EXTRACTION.format(transcript=state.call_transcript)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    response = llm.with_structured_output(SFDCUseCasesOutputState).invoke(messages)

    response_dict = response.model_dump()

    return {"new_use_cases": response_dict["new_use_cases"]}


# TODO: Implement new use case insertion
# def new_use_case_insert(state: OverallState) -> OverallState:
#     """
#     Insert new use cases into the new uses cases table.
#     """
#     session = get_snowflake_session()

#     # Compare new use case description to existing description of current use cases in SFDC table

#     # Compare new use case description to other new use cases in the new uses cases table

#     # If not already exists add it to the new uses cases table.
#     return state


# def final_results(state: OverallState) -> OutputState:
#     output_dict = state.model_dump()
#     return {
#         "new_use_cases": output_dict["new_use_cases"]
#     }


builder = StateGraph(OverallState, output_schema=OutputState)
builder.add_node("extract_transcript", extract_transcript)
# builder.add_node("sfdc_assistant", sfdc_assistant)
builder.add_node("new_use_case_assistant", new_use_case_assistant)
# builder.add_node("final_results", final_results)

builder.add_edge(START, "extract_transcript")
# builder.add_edge("extract_transcript", "sfdc_assistant")
# builder.add_edge("sfdc_assistant", "final_results")
builder.add_edge("extract_transcript", "new_use_case_assistant")
builder.add_edge("new_use_case_assistant", END)
# builder.add_edge("final_results", END)

graph = builder.compile()
