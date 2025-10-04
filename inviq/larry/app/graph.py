from langchain_core.messages import SystemMessage
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from .tools import get_next_submission, extract_fields_from_file, create_invoice, approve_invoice, reject_invoice

load_dotenv()


def create_graph():
  model = ChatOpenAI(model="gpt-4o", temperature=0)

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
  return workflow.compile()
