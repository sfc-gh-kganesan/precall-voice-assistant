from langgraph.graph import StateGraph, START, END
from typing import TypedDict


class State(TypedDict):
    input: str
    validated: bool
    processed: str
    result: dict | None


def validate_input(state: State) -> dict:
    valid = isinstance(state["input"], str) and len(state["input"].strip()) > 0
    print(f'[validate_input] input="{state["input"]}" valid={valid}')
    return {"validated": valid}


def process_data(state: State) -> dict:
    if not state["validated"]:
        return {"processed": ""}
    processed = state["input"].strip().upper()[::-1]
    print(f'[process_data] "{state["input"]}" -> "{processed}"')
    return {"processed": processed}


def format_output(state: State) -> dict:
    from datetime import datetime, timezone

    return {
        "result": {
            "original": state["input"],
            "processed": state["processed"],
            "valid": state["validated"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


workflow = StateGraph(State)
workflow.add_node("validate_input", validate_input)
workflow.add_node("process_data", process_data)
workflow.add_node("format_output", format_output)
workflow.add_edge(START, "validate_input")
workflow.add_edge("validate_input", "process_data")
workflow.add_edge("process_data", "format_output")
workflow.add_edge("format_output", END)

app = workflow.compile()


def main(sdk):
    inp = sdk.get_parameter("input")
    result = app.invoke(
        {"input": inp, "validated": False, "processed": "", "result": None}
    )
    return result["result"]
