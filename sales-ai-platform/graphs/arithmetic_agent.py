"""
Arithmetic Agent Graph

An LLM-powered agent that can perform arithmetic operations using tool calls.
Uses Snowflake Cortex inference when running in SPCS.
"""

import os
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from langgraph.graph import START, StateGraph, MessagesState
from langgraph.prebuilt import tools_condition, ToolNode


def add(a: int, b: int) -> int:
    """Adds a and b.

    Args:
        a: first int
        b: second int
    """
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiplies a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b


def divide(a: int, b: int) -> float:
    """Divide a and b.

    Args:
        a: first int
        b: second int
    """
    return a / b


tools = [add, multiply, divide]


def get_llm():
    """
    Get LLM configured for either Snowflake Cortex or OpenAI.
    
    When SNOWFLAKE_HOST is set, uses Cortex inference.
    Otherwise, uses OpenAI (requires OPENAI_API_KEY).
    
    Note: For Cortex, token is read fresh each call to handle rotation.
    """
    snowflake_host = os.getenv('SNOWFLAKE_HOST')
    
    if snowflake_host:
        # Use Snowflake Cortex inference - read token fresh each time
        from utils import get_snowflake_token
        
        base_url = f'https://{snowflake_host}/api/v2/cortex/openai'
        api_key = get_snowflake_token()  # Fresh token on each call
        
        llm = ChatOpenAI(
            model="claude-3-5-sonnet",
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            max_retries=5,
            request_timeout=20
        )
    else:
        # Use OpenAI directly
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            max_retries=5,
            request_timeout=20
        )
    
    return llm


# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked with writing performing arithmetic on a set of inputs.")


# Node - creates LLM fresh each time to handle token rotation
def assistant(state: MessagesState):
    llm = get_llm()  # Get LLM with fresh token
    llm_with_tools = llm.bind_tools(tools)
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}


# Build graph
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", "assistant")

# Compile graph
graph = builder.compile()

