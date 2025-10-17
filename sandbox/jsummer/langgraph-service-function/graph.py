import random
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# Graph state
class State(TypedDict):
    name: str
    age: int
    response: str

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

def run_workflow(name: str) -> str:
    graph = create_graph()
    result = graph.invoke({"name": name})
    return result["response"]

if __name__ == "__main__":
    name = "John"
    result = run_workflow(name)
    print(result)