/**
 * Test 3: Stateful Workflow Execution
 * Tests LangGraph StateGraph or fallback state machine
 */

import { PyodideRunner } from "../runner.js";

async function main() {
  console.log("=== Test: Stateful Workflow Execution (Node.js) ===\n");

  const runner = new PyodideRunner();
  console.log("1. Initializing Pyodide...");
  await runner.initialize();

  console.log("2. Setting up workflow...\n");

  const setupResult = await runner.runPython(`
USING_LANGGRAPH = False

try:
    from langgraph.graph import StateGraph
    from typing import TypedDict, Annotated
    from operator import add
    USING_LANGGRAPH = True
    print("Using LangGraph")
except ImportError as e:
    print(f"LangGraph not available: {e}")
    print("Using manual state machine")

if USING_LANGGRAPH:
    class WorkflowState(TypedDict):
        messages: Annotated[list[str], add]
        step_count: int
    
    def node_start(state):
        return {"messages": ["Started"], "step_count": state.get("step_count", 0) + 1}
    
    def node_process(state):
        return {"messages": [f"Processing step {state['step_count']}"], "step_count": state["step_count"] + 1}
    
    def node_end(state):
        return {"messages": ["Complete"], "step_count": state["step_count"] + 1}
    
    workflow = StateGraph(WorkflowState)
    workflow.add_node("start", node_start)
    workflow.add_node("process", node_process)
    workflow.add_node("end", node_end)
    workflow.add_edge("__start__", "start")
    workflow.add_edge("start", "process")
    workflow.add_edge("process", "end")
    workflow.add_edge("end", "__end__")
    app = workflow.compile()
else:
    class ManualWorkflow:
        def __init__(self):
            self.state = {"messages": [], "step_count": 0}
        
        def invoke(self, initial):
            self.state = {**self.state, **initial}
            self.state["messages"].append("Started")
            self.state["step_count"] += 1
            self.state["messages"].append(f"Processing step {self.state['step_count']}")
            self.state["step_count"] += 1
            self.state["messages"].append("Complete")
            self.state["step_count"] += 1
            return self.state
    
    app = ManualWorkflow()

f"Setup complete. Using LangGraph: {USING_LANGGRAPH}"
`);
  console.log(`   ${setupResult.result}\n`);

  console.log("3. Executing workflow...");
  const execResult = await runner.runPython(`
if USING_LANGGRAPH:
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        app.ainvoke({"messages": [], "step_count": 0})
    )
else:
    result = app.invoke({"messages": [], "step_count": 0})
result
`);

  if (execResult.success) {
    console.log(`   Execution time: ${execResult.executionTimeMs.toFixed(2)}ms`);
    console.log(`   Result: ${JSON.stringify(execResult.result, null, 2)}\n`);

    const result = execResult.result;
    const messagesOk = result?.messages?.length >= 3;
    const stepsOk = result?.step_count >= 3;

    console.log("4. Validation:");
    console.log(`   Messages: ${messagesOk ? "✓" : "✗"} (${result?.messages?.length || 0})`);
    console.log(`   Steps: ${stepsOk ? "✓" : "✗"} (${result?.step_count || 0})`);
  } else {
    console.log(`   Failed: ${execResult.error}\n`);
  }

  console.log("\n5. Testing async nodes...");
  const asyncResult = await runner.runPython(`
import asyncio

class AsyncWorkflow:
    def __init__(self):
        self.state = {"results": []}
    
    async def node1(self):
        await asyncio.sleep(0.01)
        self.state["results"].append("node1")
    
    async def node2(self):
        await asyncio.sleep(0.01)
        self.state["results"].append("node2")
    
    async def run(self):
        await self.node1()
        await self.node2()
        return self.state

await AsyncWorkflow().run()
`);

  if (asyncResult.success) {
    console.log(`   Result: ${JSON.stringify(asyncResult.result)}`);
    console.log(`   Async works: ✓`);
  } else {
    console.log(`   Failed: ${asyncResult.error}`);
  }

  console.log("\n=== Summary ===");
  console.log(`Workflow: ${execResult.success ? "✓" : "✗"}`);
  console.log(`Async: ${asyncResult.success ? "✓" : "✗"}`);
  console.log(`LangGraph: ${setupResult.result?.includes("True") ? "✓" : "✗ (fallback)"}`);

  process.exit(execResult.success && asyncResult.success ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
