"""
Post Meeting Workflow Graph

This workflow processes a call transcipt to extract specific information.
"""

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, Annotated
from pydantic import BaseModel, Field
from graphs.graph_utils import get_llm
from graphs.prompts import SYSTEM_PROMPT_SFDC_EXTRACTION, HUMAN_MESSAGE_SFDC_EXTRACTION
from utils import get_snowflake_session
# import json

# # Define State Schemas
class OverallState(TypedDict):
    activity_id: str
    salesforce_account_id: str
    owner_id: str
    call_transcript: str
    takeaways: str
    next_steps: list[str]
    opportunity_comments: list[str]
    deal_stage: str
    close_date: str
    opportunity_meddpicc_status: str
    new_use_cases: list[str]
    objections: list[str]

# class SFDCOutputState(TypedDict):
#     next_steps: list[str]
#     opportunity_comments: list[str]
#     deal_stage: str
#     close_date: str
#     opportunity_meddpicc_status: str
#     new_use_cases: list[str]
#     objections: list[str]

class SFDCOutputState(BaseModel):
    next_steps: Annotated[list[str], Field(description="List of next steps. If a value is not found in the call transcript, assign an empty list")]
    opportunity_comments: Annotated[list[str], Field(description="List of opportunity comments. If a value is not found in the call transcript, assign an empty list")]
    deal_stage: Annotated[str, Field(description="Deal stage. If a value is not found in the call transcript, assign an empty string")]
    close_date: Annotated[str, Field(description="Close date (in date format YYYY-MM-DD). If a value is not found in the call transcript, assign an empty string")]
    opportunity_meddpicc_status: Annotated[str, Field(description="Opportunity MEDDPICC status. If a value is not found in the call transcript, assign an empty string")]
    new_use_cases: Annotated[list[str], Field(description="List of new use cases. If a value is not found in the call transcript, assign an empty list")]
    objections: Annotated[list[str], Field(description="List of objections. If a value is not found in the call transcript, assign an empty list")]



class OutputState(TypedDict):
    next_steps: list[str]
    opportunity_comments: list[str]
    deal_stage: str
    close_date: str
    opportunity_meddpicc_status: str
    new_use_cases: list[str]
    objections: list[str]


# Create nodes
def extract_transcript(state: OverallState) -> OverallState:
    """
    Extract the call transcript from snowflake table
    """

    session = get_snowflake_session()
    #NOTE: We are hard-coding the fully-qualified table name for now.   FROM sales.engagement360_pitch.all_engagement_details 
    query = f"""
    SELECT RAW_CONTENT, TAKEAWAYS 
    FROM ai_fde.sales_ai_platform.engagement_details_test
    WHERE activity_id = '{state['activity_id']}'
    AND salesforce_account_id = '{state['salesforce_account_id']}'
    AND owner_id = '{state['owner_id']}'
    ORDER BY activity_date desc
    LIMIT 1
    """
    results = session.sql(query).collect()
    transcript = results[0]['RAW_CONTENT']
    takeaways = results[0]['TAKEAWAYS']
    return {"call_transcript": transcript, "takeaways": takeaways}

def sfdc_assistant(state: OverallState) -> OverallState:
    """
    Extract SFDC fields from the call transcript.
    """
    llm = get_llm()
    system_prompt = SYSTEM_PROMPT_SFDC_EXTRACTION
    human_prompt = HUMAN_MESSAGE_SFDC_EXTRACTION.format(transcript=state["call_transcript"])
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]

    # response = llm.invoke(messages)
    response = llm.with_structured_output(SFDCOutputState).invoke(messages)
    
    # # Format response as JSON (if using a TypedDict state)
    # try:
    #     response_dict = json.loads(response.content)
    # except json.JSONDecodeError:
    #     response_dict = {"error": "Failed to parse response as JSON"}

    # response_dict = response # If using structured output with a TypedDict state

    response_dict = response.model_dump() # If using structured output with a pydantic BaseModel state

    return {
            # "messages": [response],
            "next_steps": response_dict["next_steps"],
            "opportunity_comments": response_dict["opportunity_comments"],
            "deal_stage": response_dict["deal_stage"],
            "close_date": response_dict["close_date"],
            "opportunity_meddpicc_status": response_dict["opportunity_meddpicc_status"],
            "new_use_cases": response_dict["new_use_cases"],
            "objections": response_dict["objections"]
            }


def final_results(state: OverallState) -> OutputState:
    return {"next_steps": state["next_steps"],
            "opportunity_comments": state["opportunity_comments"],
            "deal_stage": state["deal_stage"],
            "close_date": state["close_date"],
            "opportunity_meddpicc_status": state["opportunity_meddpicc_status"],
            "new_use_cases": state["new_use_cases"],
            "objections": state["objections"]}

builder = StateGraph(OverallState, output_schema=OutputState)
builder.add_node("extract_transcript", extract_transcript)
builder.add_node("sfdc_assistant", sfdc_assistant)
builder.add_node("final_results", final_results)

builder.add_edge(START, "extract_transcript")
builder.add_edge("extract_transcript", "sfdc_assistant")
builder.add_edge("sfdc_assistant", "final_results")
builder.add_edge("final_results", END)

graph = builder.compile()