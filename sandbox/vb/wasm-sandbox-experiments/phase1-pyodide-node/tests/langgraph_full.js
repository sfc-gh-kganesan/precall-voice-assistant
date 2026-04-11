import { loadPyodide } from "pyodide";

async function main() {
  console.log("=== Test: Full LangGraph Workflow (Pyodide 0.29.3) ===\n");
  
  const py = await loadPyodide();
  await py.loadPackage("micropip");
  
  const result = await py.runPythonAsync(`
import micropip
await micropip.install('langgraph==0.0.38')

from langgraph.graph import StateGraph
from typing import TypedDict

class State(TypedDict):
    count: int
    messages: list

def increment(state):
    return {'count': state['count'] + 1}

def double(state):
    return {'count': state['count'] * 2}

def add_message(state):
    return {'messages': state['messages'] + [f"Final count: {state['count']}"]}

workflow = StateGraph(State)
workflow.add_node('increment', increment)
workflow.add_node('double', double)
workflow.add_node('message', add_message)
workflow.add_edge('increment', 'double')
workflow.add_edge('double', 'message')
workflow.set_entry_point('increment')
workflow.set_finish_point('message')
app = workflow.compile()

# Execute with await directly (no run_until_complete needed)
result = await app.ainvoke({'count': 5, 'messages': []})
result
`);
  
  console.log("Result:", py.toPy(result).toJs());
  console.log("\n✓ LangGraph workflow executed successfully in WASM!");
}

main().catch(console.error);
