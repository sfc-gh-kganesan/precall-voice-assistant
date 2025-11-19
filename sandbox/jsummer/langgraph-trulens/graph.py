# Core LangChain and LangGraph imports
from langchain_core.tools import Tool, tool
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes

from model import CortexModel

from prompts import SYSTEM_PROMPT

@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a / b


@tool
def subtract(a: int, b: int) -> int:
    """Subtract `b` from `a`.

    Args:
        a: First int
        b: Second int
    """
    return a - b

tools = [multiply, add, divide, subtract]

def get_model_with_tools(tools: list[Tool]|None = None, tool_choice: str = "auto") -> ChatOpenAI:
    """
    Get the model with the tools bound to it.
    """

    model = CortexModel().get_llm()

    if tools:
        return model.bind_tools(tools, tool_choice=tool_choice)
    else:
        return model

def create_graph():
    """
    Create the graph.
    """
    model = get_model_with_tools()

    @instrument(span_type=SpanAttributes.SpanType.GENERATION)
    def call_llm(state: MessagesState):
        """
        Invokes the LLM to get a response or a tool call.
        """
        system_message = SYSTEM_PROMPT.format(tools=tools)
        messages = [SystemMessage(content=system_message)] + state["messages"]  
        # The 'messages' are a list, we pass the current history to the model
        response = model.invoke(messages)
        
        # Return the new message to be added to the state
        return {"messages": [response]}

    # Initialize the graph with the defined state
    workflow = StateGraph(MessagesState)

    workflow.add_node("llm", call_llm)
    if tools:
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_edge("tools", "llm")
        workflow.add_conditional_edges("llm", tools_condition)

    workflow.set_entry_point("llm")

    # Compile the graph
    graph = workflow.compile()

    return graph