import logging
from typing import List

from langgraph.graph import StateGraph, START, MessagesState, END
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode, tools_condition

from .agent import Agent
from .utils import ContextSchema, get_persistent_connection
from .tools import return_final_result

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def should_continue(state: MessagesState) -> str:
    """
    Determine whether to continue to tools or go to return_final_result.
    Returns 'tools' if there are other tool calls, 'return_final_result' if return_final_result is called.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        # Check if return_final_result is being called
        for tool_call in last_message.tool_calls:
            if tool_call['name'] == 'return_final_result':
                return "return_final_result"
        # Other tool calls
        return "tools"
    
    # No tool calls, end the workflow
    return "__end__"


def create_graph():

    try:
        agent = Agent()
    except Exception as e:
        logger.error(f"Error initializing agent: {str(e)}")
        raise Exception(f"Error initializing agent: {str(e)}")

    def add_system_message(state: MessagesState) -> MessagesState:
        return {"messages": [SystemMessage(content=agent.system_message)] + state["messages"]}

    def call_model(state: MessagesState) -> MessagesState:

        try:

            return {"messages": agent.model.invoke(state["messages"])}
        except Exception as e:
                # Return an AI message with the error instead of crashing
            logger.error(f"Error in call_model: {str(e)}")
            error_message = AIMessage(
                content=f"I encountered an error while processing your request: {str(e)}."
            )
            return {"messages": [error_message]}


    workflow = StateGraph(MessagesState, context_schema=ContextSchema)
    workflow.add_node("system_message", add_system_message)
    workflow.add_node("model", call_model)
    workflow.add_edge(START, "system_message")
    workflow.add_edge("system_message", "model")

    if agent.tools:
        # Create separate tool nodes for regular tools and return_final_result
        regular_tools = [tool for tool in agent.tools if tool.name != 'return_final_result']
        final_tool = [tool for tool in agent.tools if tool.name == 'return_final_result']
        
        if regular_tools:
            workflow.add_node("tools", ToolNode(regular_tools))
        
        if final_tool:
            workflow.add_node("return_final_result", ToolNode(final_tool))
        
        # Set up conditional edges
        should_continue_edges = {"__end__": END}
        if regular_tools:
            should_continue_edges["tools"] = "tools"
        if final_tool:
            should_continue_edges["return_final_result"] = "return_final_result"
        
        workflow.add_conditional_edges("model", should_continue, should_continue_edges)
        
        if regular_tools:
            workflow.add_edge("tools", "model")
        
        if final_tool:
            workflow.add_edge("return_final_result", END)

    return workflow.compile()


def run_workflow(input: str) -> List[BaseMessage]|str:

    try:
            connection = get_persistent_connection()
    except Exception as e:
        logger.error(f"Error getting connection: {str(e)}")
        return f"Error: Failed to get connection: {str(e)}"

    try:
        graph = create_graph()
        logger.info(f"Invoking graph with input: {input}")
        inputs = {
            "messages": [HumanMessage(content=input)],
        }
        result = graph.invoke(inputs, context={"connection": connection})
        logger.info("Graph result received")
        ai_response = result["messages"][-1].content
        connection.close() # Close connection after graph invocation completes for single record
        return ai_response
        
    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}")
        return f"Error: Failed to run workflow: {str(e)}"