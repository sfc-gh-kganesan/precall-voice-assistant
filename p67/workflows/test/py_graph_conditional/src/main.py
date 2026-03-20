import re
from langgraph.graph import StateGraph, START, END
from typing import TypedDict


class State(TypedDict):
    input: str
    category: str
    response: str
    result: dict | None


def classify_input(state: State) -> dict:
    lower = state["input"].lower().strip()

    if re.match(r"^(hi|hello|hey|howdy|greetings)", lower):
        category = "greeting"
    elif (
        lower.endswith("?")
        or lower.startswith("what")
        or lower.startswith("how")
        or lower.startswith("why")
        or lower.startswith("when")
        or lower.startswith("where")
        or lower.startswith("who")
    ):
        category = "question"
    else:
        category = "statement"

    print(f'[classify_input] "{state["input"]}" -> category="{category}"')
    return {"category": category}


def route_by_category(state: State) -> str:
    match state["category"]:
        case "greeting":
            return "handle_greeting"
        case "question":
            return "handle_question"
        case _:
            return "handle_statement"


def handle_greeting(state: State) -> dict:
    print("[handle_greeting] Responding to greeting")
    return {"response": f'Hello! You said: "{state["input"]}". Nice to meet you!'}


def handle_question(state: State) -> dict:
    print("[handle_question] Responding to question")
    return {
        "response": f'Great question! You asked: "{state["input"]}". I\'d need more context to answer that properly.'
    }


def handle_statement(state: State) -> dict:
    print("[handle_statement] Responding to statement")
    return {
        "response": f'Noted. You stated: "{state["input"]}". That\'s been recorded.'
    }


def format_response(state: State) -> dict:
    from datetime import datetime, timezone

    return {
        "result": {
            "input": state["input"],
            "category": state["category"],
            "response": state["response"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


workflow = StateGraph(State)
workflow.add_node("classify_input", classify_input)
workflow.add_node("handle_greeting", handle_greeting)
workflow.add_node("handle_question", handle_question)
workflow.add_node("handle_statement", handle_statement)
workflow.add_node("format_response", format_response)
workflow.add_edge(START, "classify_input")
workflow.add_conditional_edges(
    "classify_input",
    route_by_category,
    {
        "handle_greeting": "handle_greeting",
        "handle_question": "handle_question",
        "handle_statement": "handle_statement",
    },
)
workflow.add_edge("handle_greeting", "format_response")
workflow.add_edge("handle_question", "format_response")
workflow.add_edge("handle_statement", "format_response")
workflow.add_edge("format_response", END)

app = workflow.compile()


def main(sdk):
    inp = sdk.get_parameter("input")
    result = app.invoke(
        {"input": inp, "category": "", "response": "", "result": None}
    )
    return result["result"]
