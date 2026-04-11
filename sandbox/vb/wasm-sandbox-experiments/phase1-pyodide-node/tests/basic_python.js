/**
 * Test 1: Basic Pyodide Execution
 * Validates Pyodide loads and executes Python in Node.js
 */

import { PyodideRunner } from "../runner.js";

async function main() {
  console.log("=== Test: Basic Pyodide Execution (Node.js) ===\n");

  console.log("1. Cold start initialization...");
  const runner = new PyodideRunner();
  const initTime = await runner.initialize();
  console.log(`   Cold start time: ${initTime.toFixed(2)}ms\n`);

  console.log("2. Running simple calculation...");
  const calcResult = await runner.runPython(`
result = sum(range(1, 101))
result
`);
  console.log(`   Result: ${calcResult.result}`);
  console.log(`   Expected: 5050`);
  console.log(`   Success: ${calcResult.result === 5050}`);
  console.log(`   Execution time: ${calcResult.executionTimeMs.toFixed(2)}ms\n`);

  console.log("3. Running string manipulation...");
  const strResult = await runner.runPython(`
text = "Hello, Pyodide!"
text.upper()
`);
  console.log(`   Result: ${strResult.result}`);
  console.log(`   Success: ${strResult.result === "HELLO, PYODIDE!"}\n`);

  console.log("4. Testing error handling...");
  const errorResult = await runner.runPython(`
raise ValueError("Test error")
`);
  console.log(`   Success: ${!errorResult.success}`);
  console.log(`   Error captured: ${errorResult.error?.includes("ValueError")}\n`);

  console.log("5. Testing async execution...");
  const asyncResult = await runner.runPython(`
import asyncio

async def async_sum():
    await asyncio.sleep(0.01)
    return 42

await async_sum()
`);
  console.log(`   Result: ${asyncResult.result}`);
  console.log(`   Success: ${asyncResult.result === 42}\n`);

  console.log("=== Summary ===");
  console.log(`Cold start: ${initTime.toFixed(2)}ms`);
  const allPassed =
    calcResult.result === 5050 &&
    strResult.result === "HELLO, PYODIDE!" &&
    !errorResult.success &&
    asyncResult.result === 42;
  console.log(`All tests passed: ${allPassed}`);

  process.exit(allPassed ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
