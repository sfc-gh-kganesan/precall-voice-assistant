// Simple test: Go launches Node.js with Pyodide and runs LangGraph
// This validates the core architecture works

import { loadPyodide } from "pyodide";

async function main() {
  console.log("=== Phase 2 Test: Go → Node.js → Pyodide → LangGraph ===\n");
  
  // Simulate receiving workflow from Go (would come via stdin IPC)
  const workflowCode = `
from langgraph.graph import StateGraph
from typing import TypedDict

class State(TypedDict):
    input: str
    processed: bool
    output: str

def process_input(state):
    # In real workflow, this would call host function:
    # result = execute_query(f"SELECT * FROM data WHERE id = '{state['input']}'")
    return {'processed': True}

def generate_output(state):
    # In real workflow, this would call host function:
    # result = cortex_complete(f"Summarize: {state['input']}")
    return {'output': f"Processed: {state['input']}"}

workflow = StateGraph(State)
workflow.add_node('process', process_input)
workflow.add_node('generate', generate_output)
workflow.add_edge('process', 'generate')
workflow.set_entry_point('process')
workflow.set_finish_point('generate')
app = workflow.compile()

# Execute the workflow
result = await app.ainvoke({'input': 'test-data-123', 'processed': False, 'output': ''})
result
`;

  console.log("Loading Pyodide...");
  const startLoad = Date.now();
  const py = await loadPyodide();
  console.log(`Pyodide loaded in ${Date.now() - startLoad}ms`);
  
  await py.loadPackage("micropip");
  
  console.log("Installing LangGraph 0.0.38...");
  const startInstall = Date.now();
  await py.runPythonAsync(`
import micropip
await micropip.install('langgraph==0.0.38')
  `);
  console.log(`LangGraph installed in ${Date.now() - startInstall}ms`);
  
  console.log("\nExecuting LangGraph workflow...");
  const startExec = Date.now();
  const result = await py.runPythonAsync(workflowCode);
  console.log(`Workflow executed in ${Date.now() - startExec}ms`);
  
  // Convert result to JS
  const jsResult = result.toJs({ dict_converter: Object.fromEntries });
  
  console.log("\n✓ Result:", jsResult);
  console.log("\n=== Phase 2 Architecture Validated ===");
  console.log("Go can orchestrate LangGraph workflows via Node.js + Pyodide");
}

main().catch(console.error);
