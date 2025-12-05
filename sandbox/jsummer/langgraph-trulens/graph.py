import logging

from langchain_core.tools import Tool, tool
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes

from model import CortexModel
from prompts import SYSTEM_PROMPT
from utils import application_name, tracer

logger = logging.getLogger(application_name)

@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    with tracer.start_as_current_span("tool.multiply") as span:
        span.set_attribute("tool.input.a", a)
        span.set_attribute("tool.input.b", b)
        logger.info(f"Multiplying {a} and {b}", extra={"a": a, "b": b})
        result = a * b
        span.set_attribute("tool.output", result)
        return result


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    with tracer.start_as_current_span("tool.add") as span:
        span.set_attribute("tool.input.a", a)
        span.set_attribute("tool.input.b", b)
        logger.info(f"Adding {a} and {b}", extra={"a": a, "b": b})
        result = a + b
        span.set_attribute("tool.output", result)
        return result


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    with tracer.start_as_current_span("tool.divide") as span:
        span.set_attribute("tool.input.a", a)
        span.set_attribute("tool.input.b", b)
        logger.info(f"Dividing {a} by {b}", extra={"a": a, "b": b})
        result = a / b
        span.set_attribute("tool.output", result)
        return result


@tool
def subtract(a: int, b: int) -> int:
    """Subtract `b` from `a`.

    Args:
        a: First int
        b: Second int
    """
    with tracer.start_as_current_span("tool.subtract") as span:
        span.set_attribute("tool.input.a", a)
        span.set_attribute("tool.input.b", b)
        logger.info(f"Subtracting {b} from {a}", extra={"a": a, "b": b})
        result = a - b
        span.set_attribute("tool.output", result)
        return result

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
    model = get_model_with_tools(tools)

    @instrument(span_type=SpanAttributes.SpanType.GENERATION)
    def call_llm(state: MessagesState):
        """
        Invokes the LLM to get a response or a tool call.
        """
        with tracer.start_as_current_span("llm.invoke") as span:
            span.set_attribute("llm.message_count", len(state["messages"]))
            span.set_attribute("llm.mytest", "jason_test")
            logger.info(f"Invoking LLM with tools.")
            system_message = SYSTEM_PROMPT.format(tools=tools)
            messages = [SystemMessage(content=system_message)] + state["messages"]  
            # The 'messages' are a list, we pass the current history to the model
            response = model.invoke(messages)
            
            span.set_attribute("llm.response_type", type(response).__name__)
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