"""
Greeting Workflow Graph

A simple workflow that generates personalized greetings with random ages.
Demonstrates basic state management and sequential node execution.
"""

import random
from typing import Any, Optional

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END


# ============================================================================
# State Schema
# ============================================================================

class GreetingState(BaseModel):
    """State model for the greeting workflow graph."""
    
    name: str = Field(
        description="The name of the person to greet"
    )
    age: Optional[int] = Field(
        default=None,
        description="Randomly generated age"
    )
    response: Optional[str] = Field(
        default=None,
        description="The generated greeting message"
    )
    
    class Config:
        """Pydantic config for the state model."""
        arbitrary_types_allowed = True


def first_node(state: GreetingState) -> dict:
    """Generate a random age."""
    age = random.randint(1, 100)
    return {"age": age}


def second_node(state: GreetingState) -> dict:
    """Create a personalized greeting message."""
    response = f"Hello, {state.name}! I can't believe it's your {state.age} birthday."
    return {"response": response}


def create_graph():
    """Create and compile the greeting workflow graph."""
    workflow = StateGraph(GreetingState)

    workflow.add_node("first_node", first_node)
    workflow.add_node("second_node", second_node)

    workflow.add_edge(START, "first_node")
    workflow.add_edge("first_node", "second_node")
    workflow.add_edge("second_node", END)

    return workflow.compile()


async def run_workflow(args: Any) -> GreetingState:
    """
    Manages the passing from the endpoint to the graph invocation.

    Critical to wrap this in a try/except block to handle any errors that may occur.
    If running in SPCS against a batch of rows, a single error will cause the entire batch to fail.

    Args:
        args: The input to the workflow. Can be:
            - dict: Must contain 'name' key
            - str: Used as the name
            - GreetingState: Pydantic model instance

    Returns:
        The result of the workflow as a GreetingState instance
    """
    graph_instance = create_graph()

    if isinstance(args, GreetingState):
        inputs = args.model_dump()
    elif isinstance(args, dict):
        if "name" not in args:
            raise ValueError("Missing required argument: name")
        inputs = args
    elif isinstance(args, str):
        inputs = {"name": args}
    else:
        raise ValueError(f"Invalid input type passed to run_workflow: {type(args)}")

    result = await graph_instance.ainvoke(inputs)
    return GreetingState(**result)


# Export the compiled graph for LangGraph Studio
graph = create_graph()

