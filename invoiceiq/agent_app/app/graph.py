from langgraph.graph import StateGraph, START, MessagesState
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.prebuilt import ToolNode, tools_condition

from .agent import Agent


def create_graph():

    try:
        agent = Agent()
    except Exception as e:
        raise Exception(f"Error initializing agent: {str(e)}")

    def add_system_message(state: MessagesState) -> MessagesState:
        return {"messages": [SystemMessage(content=agent.system_message)] + state["messages"]}

    def call_model(state: MessagesState) -> MessagesState:

        try:

            return {"messages": agent.model.invoke(state["messages"])}
        except Exception as e:
                # Return an AI message with the error instead of crashing
            error_message = AIMessage(
                content=f"I encountered an error while processing your request: {str(e)}."
            )
            return {"messages": [error_message]}

    workflow = StateGraph(MessagesState)
    workflow.add_node("system_message", add_system_message)
    workflow.add_node("model", call_model)
    workflow.add_edge(START, "system_message")
    workflow.add_edge("system_message", "model")

    if agent.tools:        

        workflow.add_node("tools", ToolNode(agent.tools))
        workflow.add_conditional_edges("model", tools_condition)
        workflow.add_edge("tools", "model")

    return workflow.compile()