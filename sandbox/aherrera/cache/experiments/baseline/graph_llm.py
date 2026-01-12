"""Baseline LangGraph experiment with Cortex LLM.

Based on jsummer/langgraph-trulens pattern.
No caching - establishes baseline performance metrics.
"""
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes

from shared.cortex_models import CortexLLM
from shared.tools import MATH_TOOLS
from shared.utils import application_name, tracer

logger = logging.getLogger(application_name)

SYSTEM_PROMPT = """You are a helpful AI assistant that can perform mathematical calculations.

You have access to the following tools:
{tools}

Use the tools to answer the user's question accurately."""


def get_model_with_tools(tools=None, tool_choice="auto"):
    """Get Cortex LLM model with tools bound."""
    cortex_llm = CortexLLM(model_name="claude-3-5-sonnet")
    model = cortex_llm.get_llm()

    if tools:
        return model.bind_tools(tools, tool_choice=tool_choice)
    else:
        return model


def create_graph():
    """Create LangGraph workflow with Cortex LLM."""
    model = get_model_with_tools(MATH_TOOLS)

    @instrument(span_type=SpanAttributes.SpanType.GENERATION)
    def call_llm(state: MessagesState):
        """Invoke Cortex LLM to get response or tool call."""
        with tracer.start_as_current_span("llm.invoke") as span:
            span.set_attribute("llm.message_count", len(state["messages"]))
            logger.info(f"Invoking Cortex LLM with {len(MATH_TOOLS)} tools")

            system_message = SYSTEM_PROMPT.format(tools=MATH_TOOLS)
            messages = [SystemMessage(content=system_message)] + state["messages"]

            response = model.invoke(messages)

            span.set_attribute("llm.response_type", type(response).__name__)
            return {"messages": [response]}

    # Initialize graph
    workflow = StateGraph(MessagesState)

    workflow.add_node("llm", call_llm)
    if MATH_TOOLS:
        workflow.add_node("tools", ToolNode(MATH_TOOLS))
        workflow.add_edge("tools", "llm")
        workflow.add_conditional_edges("llm", tools_condition)

    workflow.set_entry_point("llm")

    # Compile graph
    graph = workflow.compile()

    return graph


if __name__ == "__main__":
    # Quick test
    graph = create_graph()

    test_query = "What is 15 multiplied by 4?"
    state = {"messages": [HumanMessage(content=test_query)]}

    logger.info(f"Testing baseline graph with query: {test_query}")
    result = graph.invoke(state)

    if "messages" in result and len(result["messages"]) > 0:
        answer = result["messages"][-1].content
        logger.info(f"Answer: {answer}")
        print(f"Q: {test_query}")
        print(f"A: {answer}")
    else:
        logger.error("No response from model")
        print("Error: No response from model")
