import random
from typing import TypedDict, Any, NotRequired

from langgraph.graph import StateGraph, START, END


# Graph state
class State(TypedDict):
    name: str
    age: NotRequired[int]
    response: NotRequired[str]

def first_node(state: State) -> State:
    age = random.randint(1, 100)
    return {"age": age}

def second_node(state: State) -> State:
    response = f"Hello, {state['name']}! I can't believe it's your {state['age']} birthday."
    return {"response": response}

def create_graph():
    workflow = StateGraph(State)

    workflow.add_node("first_node", first_node)
    workflow.add_node("second_node", second_node)

    workflow.add_edge(START, "first_node")
    workflow.add_edge("first_node", "second_node")
    workflow.add_edge("second_node", END)

    return workflow.compile()

async def run_workflow(args: Any) -> str:
    """
    Manages the passing from the endpoint to the graph invocation.

    Critical to wrap this in a try/except block to handle any errors that may occur.
    If running in SPCS against a batch of rows, a single error will cause the entire batch to fail.

    Args:
        args: The input to the workflow

    Returns:
        The result of the workflow
    """

    try:
        graph = create_graph()

        # We will assume that the required keys are the same as the keys in the State class.
        # Only the ones not marked as NotRequired are necessay at graph startup.
        # We will also assume they're passed in the same order as the State class.
        required_names = list(State.__required_keys__)

        if isinstance(args, dict):
            if not all(name in args for name in required_names):
                raise ValueError(f"Missing required arguments: {required_names}")
            inputs = args
        elif isinstance(args, str):
            inputs = {required_names[0]: args}
        elif isinstance(args, list):
            inputs = {arg_name: arg for arg_name, arg in zip(required_names, args)}
        else:
            raise ValueError(f"Invalid input type passed to run_workflow: {type(args)}")

        result = await graph.ainvoke(inputs)
        return result["response"]
    except Exception as e:
        return f"Error running workflow: {str(e)}"