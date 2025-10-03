from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from dotenv import load_dotenv
import os
import random

# We will use this model for both the conversation and the summarization
from langchain_openai import ChatOpenAI

load_dotenv()

# cortex_pat=os.getenv("CORTEX_PAT", "")
# cortex_endpoint=os.getenv("CORTEX_ENDPOINT", "")
#
# print(cortex_pat)
# print(cortex_endpoint)
# model = ChatOpenAI(model="claude-4-sonnet", temperature=0, api_key=cortex_pat, base_url=cortex_endpoint)

model = ChatOpenAI(model="gpt-4o", temperature=0)


def get_next_submission() -> dict:
  """Retrieve the next submission to process from the InvoiceStore service.
  """
  return {
      "lift_ticket": "LIFT-12345",
      "submission_id": "3",
      "file_ids": ["id-123", "id-345"],
  }


def extract_fields_from_file(file_id: str) -> dict:
  """Use this tool to extract data fields from an invoice file.

  Args:
    file_id: the file identifier str
  """
  print(f"extracting file {file_id}")
  return {
      "invoice_number": f"foobar-{random.randint(1, 100)}",
      "total_amount": f"${random.randint(200, 3000)}.00",
      "vendor_name": "Shadow Corp",
  }


def create_invoice(submission_id: str, total_amount: str, vendor_name: str, invoice_number: str) -> dict:
  """Use this tool to create a new invoice record using data extracted from an invoice file.

  Args:
    submission_id: the submission this invoice was associated with str
    total_amount: the total_amount field value extracted from the invoice
    vendor_name: the vendor_name field value extracted from the invoice
    invoice_number: the invoice_number field value extracted from the invoice
  """
  return {
      "success": True,
      "invoice_id": f"inv-{random.randint(10, 20)}"
    }


def approve_invoice(invoice_id: str) -> bool:
  """Mark an invoice as approved

  Args:
    invoice_id: the id which identifies the invoice to approve

  Returns:
    true if invoice was successfully approved
    false if something went wrong
  """
  return True



def reject_invoice(invoice_id: str) -> bool:
  """Mark an invoice as rejected

  Args:
    invoice_id: the id which identifies the invoice to reject

  Returns:
    true if invoice was successfully rejected
    false if something went wrong
  """
  return True


tools = [get_next_submission, extract_fields_from_file, create_invoice, approve_invoice, reject_invoice]
llm = model.bind_tools(tools)

# State class to store messages and summary
class State(MessagesState):
  pass

# Define the logic to call the model
def call_model(state: State):

  system_message = """
    You are a skilled finance analyst and your task is to process and reconcile vendor invoices.
    Vendors submit invoices to your company, and you can use the get_next_submission tool to retrieve the
    next submission you should process.

    Each submission includes:
      * lift_ticket -- a reference used to look up the submission in ServiceNow
      * submission_id -- the identifier of the submission
      * file_ids -- a list of files that were submitted

    Your job is to follow this workflow:
      1. Retrieve the next submission to process
      2. If the submission has multiple files, then process each file as a separate invoice
      3. Extract fields from each file in the submission
      4. Validate the field values (see validation rules below)
      5. If the invoice is valid, mark it as approved
      6. Otherwise, mark it as rejected.
      7. Return a summary of what you did.


    Invoice validation rules:
      - Each invoice MUST contain a vendor_name, invoice_number, and total_amount
      - If the total_amount is more than $2000.00, then there must be a valid purchase_order_number included

    Let's get to work on processing the next submission!
    """
  messages = [SystemMessage(content=system_message)] + state["messages"]
  response = llm.invoke(messages)
  return {"messages": response}


# Define a new graph
workflow = StateGraph(State)
workflow.add_node("assistant", call_model)
workflow.add_node("tools", ToolNode(tools))

# Set the entrypoint as conversation
workflow.add_edge(START, "assistant")
workflow.add_conditional_edges("assistant", tools_condition)
workflow.add_edge("tools", "assistant")

# Compile
graph = workflow.compile()

if __name__ == "__main__":
  messages = graph.invoke({"messages": []})
  for m in messages['messages']:
    m.pretty_print()
