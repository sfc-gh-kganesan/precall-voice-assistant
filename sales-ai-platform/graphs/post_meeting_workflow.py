"""
Post Meeting Workflow Graph

This workflow processes a call transcipt to extract specific information.
"""

import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from snowflake.snowpark import functions as F

from graphs.graph_utils import get_llm
from graphs.prompts import HUMAN_MESSAGE_USE_CASE_DEDUP, HUMAN_MESSAGE_USE_CASE_EXTRACTION, SYSTEM_PROMPT_USE_CASE_DEDUP, SYSTEM_PROMPT_USE_CASE_EXTRACTION
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


# Pydantic model for the structured output of the use case extraction
class SFDCUseCasesStructuredOutputState(BaseModel):
    new_use_cases: list[UseCaseItem] = Field(default_factory=list, description="List of new use cases identified. (Leave empty if no use cases were discussed)")


# Pydantic model for the structured output of the use case deduplication
class DedupeStructuredOutputState(BaseModel):
    proposed_new_use_case_name: str = Field(default="", description="Name of the proposed new use case")
    is_duplicate: int = Field(default=0, description="1 if the proposed new use case is a duplicate of an existing use case, 0 otherwise.")
    duplicate_use_case_id: str = Field(default="", description="ID of the existing use case that is a duplicate of the proposed new use case.")
    duplicate_use_case_name: str = Field(default="", description="Name of the existing use case that is a duplicate of the proposed new use case.")


# Overall State
class OverallState(BaseModel):
    activity_id: str = Field(default="", description="Activity ID")
    salesforce_account_id: str = Field(default="", description="Salesforce Account ID")
    owner_id: str = Field(default="", description="Owner ID")
    call_transcript: str = Field(default="", description="Call transcript")
    takeaways: str = Field(default="", description="Takeaways")
    activity_date: str = Field(default="", description="Activity date")
    new_use_cases: list[UseCaseItem] = Field(default_factory=list, description="List of new use cases identified.")
    call_activity_previously_processed: bool = Field(default=False, description="True if the call activity has already been processed, False otherwise.")
    new_use_case_records_inserted: int = Field(default=0, description="Number of new use case records inserted into the new uses cases table.")
    new_use_case_dedup_results: list[DedupeStructuredOutputState] = Field(default_factory=list, description="List of deduplication results for the new use cases.")


# Final output state of the entire graph
class OutputState(BaseModel):
    new_use_cases: list[UseCaseItem] = Field(default_factory=list, description="List of new use cases identified")
    call_activity_previously_processed: bool = Field(default=False, description="True if the call activity has already been processed, False otherwise.")
    new_use_case_records_inserted: int = Field(default=0, description="Number of new use case records inserted into the new uses cases table.")
    new_use_case_dedup_results: list[DedupeStructuredOutputState] = Field(default_factory=list, description="List of deduplication results for the new use cases.")


# Create nodes
def extract_transcript(state: OverallState) -> OverallState:
    """
    Extract the call transcript from snowflake table
    """

    session = get_snowflake_session()

    # Use synthetic data table for demo mode, otherwise use production table
    table_name = "ai_fde.sales_ai_platform.all_engagement_details_synthetic" if os.getenv("DEMO_MODE", "false").lower() == "true" else "sales.engagement360_pitch.all_engagement_details"

    query = f"""
    SELECT RAW_CONTENT, TAKEAWAYS, ACTIVITY_DATE
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
    activity_date = results[0]["ACTIVITY_DATE"]
    return {"call_transcript": transcript, "takeaways": takeaways, "activity_date": str(activity_date)}


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

    response = llm.with_structured_output(SFDCUseCasesStructuredOutputState).invoke(messages)

    response_dict = response.model_dump()

    return {"new_use_cases": response_dict["new_use_cases"]}

    # # TODO: Maybe create a node that uses cortex search to find the most similar SFDC use case (or 2) to the new use case and saves the ID in a col.
    # def find_most_similar_sfdc_use_case(state: OverallState) -> OverallState:
    #     """
    #     Find the most similar SFDC use case to the new use case.
    #     """
    #     session = get_snowflake_session()

    #     state_dict = state.model_dump()

    #     activity_date = state_dict["activity_date"]
    #     activity_id = state_dict["activity_id"]
    #     owner_id = state_dict["owner_id"]
    #     salesforce_account_id = state_dict["salesforce_account_id"]
    #     new_use_cases_list = state_dict["new_use_cases"]

    #     # Get all of the sfdc use cases created in the last 2 years
    #     sfdc_use_cases_tbl_df = session.sql(f"""
    #         select OWNER_ID,
    #             VH_ACCOUNT_C as SALESFORCE_ACCOUNT_ID,
    #             VH_NAME_C as USE_CASE_NAME,
    #             VH_DESCRIPTION_C as USE_CASE_DESCRIPTION,
    #             object_construct('use_case_description', VH_DESCRIPTION_C, 'use_case_name', VH_NAME_C) as use_case_summary
    #         from SALES.KNOWLEDGE_ASSISTANT.VH_DELIVERABLE_C
    #         where VH_NAME_C is not null
    #             and VH_DESCRIPTION_C is not null
    #             and CREATED_DATE > dateadd('year', -2, CURRENT_DATE())
    #             and OWNER_ID = '{owner_id}'
    #             and VH_ACCOUNT_C = '{salesforce_account_id}'
    #     """)

    return {"most_similar_sfdc_use_case_id": "123"}


# New use case insertion
def new_use_case_insert(state: OverallState) -> OverallState:
    """
    Insert new use cases that were extracted from a single call transcript into the new uses cases table.
    """
    session = get_snowflake_session()

    state_dict = state.model_dump()

    activity_date = state_dict["activity_date"]
    activity_id = state_dict["activity_id"]
    owner_id = state_dict["owner_id"]
    salesforce_account_id = state_dict["salesforce_account_id"]
    new_use_cases_list = state_dict["new_use_cases"]

    DATABASE = os.getenv("DATABASE")
    SCHEMA = os.getenv("SCHEMA")
    POTENTIAL_NEW_USE_CASES_TBL_NM = "potential_new_use_cases"

    new_use_case_records_inserted = 0
    dedup_results_list = []

    # ------------------------------------------------------------
    # Check if the call was previously processed, with extracted use cases already inserted into the new uses cases table.
    #  If the use cases from that call are already in the new uses cases table, do not insert them again.
    # ------------------------------------------------------------
    call_already_exists_in_new_use_cases_table = (session.table(f"{DATABASE}.{SCHEMA}.{POTENTIAL_NEW_USE_CASES_TBL_NM}").filter(F.col("activity_id") == activity_id).filter(F.col("owner_id") == owner_id).filter(F.col("salesforce_account_id") == salesforce_account_id).count()) > 0
    # ------------------------------------------------------------

    # If the length of the new use cases list is greater than 0 and the call does not already exist in the new use cases table, insert the new use cases into the new uses cases table.
    if len(new_use_cases_list) > 0 and not call_already_exists_in_new_use_cases_table:
        for new_use_case in new_use_cases_list:
            new_use_case_description = new_use_case["use_case_description"]
            new_use_case_name = new_use_case["use_case_name"]
            new_use_case_workloads = new_use_case["workloads"]
            new_use_case_technical_use_cases = new_use_case["technical_use_cases"]
            new_use_case_incumbent_vendor = new_use_case["incumbent_vendor"]

            # ------------------------------------------------------------
            # Use an LLM to compare new use case description to other new use cases in the new uses cases table and to most recent 5 existing descriptions of current use cases in SFDC table.
            # NOTE: 95% of the accounts have less than 5 existing use cases created in the last 6 months in the SFDC table.
            # ------------------------------------------------------------
            previous_use_cases_df = session.sql(f"""
            with extracted_use_case_summaries as (
                select RECORD_CREATION_DTTM,
                    new_use_case_id,
                    use_case_name,
                    use_case_description,
                    object_construct('use_case_id', new_use_case_id, 'use_case_description', use_case_description, 'use_case_name', use_case_name) as use_case_summary
                from {DATABASE}.{SCHEMA}.{POTENTIAL_NEW_USE_CASES_TBL_NM}
                where OWNER_ID = '{owner_id}'
                    and SALESFORCE_ACCOUNT_ID = '{salesforce_account_id}'
                    and RECORD_CREATION_DTTM > dateadd('month', -6, CURRENT_DATE())
            ),
            actual_use_case_summaries as (
                select CREATED_DATE,
                    ID,
                    VH_NAME_C,
                    VH_DESCRIPTION_C,
                    object_construct('use_case_id', ID, 'use_case_description', VH_DESCRIPTION_C, 'use_case_name', VH_NAME_C) as use_case_summary,
                    ROW_NUMBER() OVER (ORDER BY CREATED_DATE) as row_num
                from SALES.KNOWLEDGE_ASSISTANT.VH_DELIVERABLE_C
                where OWNER_ID = '{owner_id}'
                    and VH_ACCOUNT_C = '{salesforce_account_id}'
                    and CREATED_DATE > dateadd('month', -6, CURRENT_DATE())
                    and VH_NAME_C is not null
                    and VH_DESCRIPTION_C is not null
            ),
            unioned_summaries as (
                select use_case_summary from extracted_use_case_summaries
                union
                select use_case_summary from actual_use_case_summaries where row_num <= 5
            )
            select array_agg(use_case_summary) as USE_CASE_SUMMARY_LIST
            from unioned_summaries
            """)

            previous_use_cases_list = json.loads(previous_use_cases_df.collect()[0]["USE_CASE_SUMMARY_LIST"])

            new_use_case_summary = {
                "use_case_description": new_use_case_description,
                "use_case_name": new_use_case_name,
            }

            llm = get_llm(cortex_model_selection="openai-gpt-4.1")
            system_prompt = SYSTEM_PROMPT_USE_CASE_DEDUP
            human_prompt = HUMAN_MESSAGE_USE_CASE_DEDUP.format(proposed_new_use_case=new_use_case_summary, existing_use_cases=previous_use_cases_list)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]

            response = llm.with_structured_output(DedupeStructuredOutputState).invoke(messages)

            response_dict = response.model_dump()

            # ------------------------------------------------------------

            # If use case does not already exists add it to the new uses cases table.
            is_duplicate = response_dict.get("is_duplicate", 0)

            if is_duplicate:
                dedup_results_list.append(response_dict)
            else:
                insert_statement = f"""
                INSERT INTO {DATABASE}.{SCHEMA}.{POTENTIAL_NEW_USE_CASES_TBL_NM} (activity_date, activity_id, owner_id, salesforce_account_id, use_case_description, use_case_name, workloads, technical_use_cases, incumbent_vendor)
                    SELECT
                    '{activity_date}',
                    '{activity_id}',
                    '{owner_id}',
                    '{salesforce_account_id}',
                    $${new_use_case_description}$$,
                    $${new_use_case_name}$$,
                    {new_use_case_workloads},
                    {new_use_case_technical_use_cases},
                    $${new_use_case_incumbent_vendor}$$
                    """
                session.sql(insert_statement).collect()

                new_use_case_records_inserted += 1

    return {"call_activity_previously_processed": call_already_exists_in_new_use_cases_table, "new_use_case_records_inserted": new_use_case_records_inserted, "new_use_case_dedup_results": dedup_results_list}


# def final_results(state: OverallState) -> OutputState:
#     output_dict = state.model_dump()
#     return {
#         "new_use_cases": output_dict["new_use_cases"]
#     }


builder = StateGraph(OverallState, output_schema=OutputState)
builder.add_node("extract_transcript", extract_transcript)
# builder.add_node("sfdc_assistant", sfdc_assistant)
builder.add_node("new_use_case_assistant", new_use_case_assistant)
builder.add_node("new_use_case_insert", new_use_case_insert)
# builder.add_node("final_results", final_results)

builder.add_edge(START, "extract_transcript")
# builder.add_edge("extract_transcript", "sfdc_assistant")
# builder.add_edge("sfdc_assistant", "final_results")
builder.add_edge("extract_transcript", "new_use_case_assistant")
builder.add_edge("new_use_case_assistant", "new_use_case_insert")
builder.add_edge("new_use_case_insert", END)
# builder.add_edge("final_results", END)

graph = builder.compile()
