/**
 * Test 2: LangGraph Import
 * Tests if LangGraph can be imported in Pyodide
 */

import { PyodideRunner } from "../runner.js";

async function main() {
  console.log("=== Test: LangGraph Import (Node.js) ===\n");

  const runner = new PyodideRunner();
  console.log("1. Initializing Pyodide...");
  const initTime = await runner.initialize();
  console.log(`   Init time: ${initTime.toFixed(2)}ms\n`);

  console.log("2. Installing packages...");
  const installStart = performance.now();

  try {
    // Install packages one at a time with specific versions to avoid conflicts
    await runner.installPackages(["pydantic>=2.7.4"]);
    console.log("   Pydantic installed");
    
    await runner.installPackages(["langchain-core"]);
    console.log("   langchain-core installed");
    
    await runner.installPackages(["langgraph"]);
    console.log("   langgraph installed");
    
    console.log(`   Total install time: ${(performance.now() - installStart).toFixed(2)}ms\n`);
  } catch (e) {
    console.log(`   Install failed: ${e}\n`);
    console.log("   This is expected - langchain has many dependencies that may not work in Pyodide\n");
  }

  console.log("3. Testing imports...\n");

  console.log("   3.1 Import pydantic...");
  const pydanticResult = await runner.runPython(`
try:
    from pydantic import BaseModel
    class TestModel(BaseModel):
        name: str
        value: int
    m = TestModel(name="test", value=42)
    f"pydantic works: {m.name}={m.value}"
except Exception as e:
    f"pydantic failed: {e}"
`);
  console.log(`       ${pydanticResult.result}\n`);

  console.log("   3.2 Import typing_extensions...");
  const typingResult = await runner.runPython(`
try:
    from typing_extensions import Annotated, TypedDict
    "typing_extensions works"
except Exception as e:
    f"typing_extensions failed: {e}"
`);
  console.log(`       ${typingResult.result}\n`);

  console.log("   3.3 Import langchain_core...");
  const langchainResult = await runner.runPython(`
try:
    from langchain_core.messages import HumanMessage
    msg = HumanMessage(content="Hello")
    f"langchain_core works: {msg.content}"
except Exception as e:
    f"langchain_core failed: {e}"
`);
  console.log(`       ${langchainResult.result}\n`);

  console.log("   3.4 Import langgraph...");
  const langgraphResult = await runner.runPython(`
try:
    from langgraph.graph import StateGraph
    from typing import TypedDict
    
    class State(TypedDict):
        count: int
    
    graph = StateGraph(State)
    "langgraph works: StateGraph created"
except Exception as e:
    f"langgraph failed: {e}"
`);
  console.log(`       ${langgraphResult.result}\n`);

  console.log("=== Summary ===");
  const results = {
    pydantic: pydanticResult.result?.toString().includes("works"),
    typing_extensions: typingResult.result?.toString().includes("works"),
    langchain_core: langchainResult.result?.toString().includes("works"),
    langgraph: langgraphResult.result?.toString().includes("works"),
  };

  for (const [pkg, works] of Object.entries(results)) {
    console.log(`${pkg}: ${works ? "✓" : "✗"}`);
  }

  process.exit(results.langgraph ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
