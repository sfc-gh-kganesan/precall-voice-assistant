/**
 * Test 4: Host Functions
 * Tests SDK-like host function calls from Python
 */

import { PyodidePool, PyodideRunner } from "../runner.js";

const mockDatabase = {
  users: [
    { id: 1, name: "Alice", role: "admin" },
    { id: 2, name: "Bob", role: "user" },
    { id: 3, name: "Charlie", role: "user" },
  ],
};

async function main() {
  console.log("=== Test: Host Functions (Node.js) ===\n");

  const runner = new PyodideRunner();

  console.log("1. Registering host functions...");

  runner.registerHostFunction("execute_query", async (params) => {
    console.log(`   [Host] execute_query: ${params.sql}`);
    if (params.sql.toLowerCase().includes("select * from users")) {
      return { rows: mockDatabase.users, rowCount: mockDatabase.users.length };
    }
    return { rows: [], rowCount: 0 };
  });

  runner.registerHostFunction("cortex_complete", async (params) => {
    const last = params.messages[params.messages.length - 1];
    console.log(`   [Host] cortex_complete: "${last?.content?.substring(0, 40)}..."`);
    return {
      success: true,
      choices: [{ message: { role: "assistant", content: `Response to: ${last?.content?.substring(0, 20)}` } }],
    };
  });

  runner.registerHostFunction("http_request", async (params) => {
    console.log(`   [Host] http_request: ${params.url}`);
    return { status: 200, body: { mock: true } };
  });

  console.log("   Registered: execute_query, cortex_complete, http_request\n");

  console.log("2. Initializing Pyodide...");
  const initTime = await runner.initialize();
  console.log(`   Init time: ${initTime.toFixed(2)}ms\n`);

  console.log("3. Testing execute_query...");
  const queryResult = await runner.runPython(`
result = await sdk.execute_query("SELECT * FROM users")
result
`);
  console.log(`   Result: ${JSON.stringify(queryResult.result)}`);
  console.log(`   Success: ${queryResult.success}\n`);

  console.log("4. Testing cortex_complete...");
  const llmResult = await runner.runPython(`
result = await sdk.cortex_complete(
    model="claude-4-sonnet",
    messages=[{"role": "user", "content": "What is 2+2?"}]
)
result
`);
  console.log(`   Result: ${JSON.stringify(llmResult.result)}`);
  console.log(`   Success: ${llmResult.success}\n`);

  console.log("5. Testing workflow with SDK...");
  const workflowResult = await runner.runPython(`
async def workflow():
    users = await sdk.execute_query("SELECT * FROM users")
    count = len(users.get("rows", []))
    
    summary = await sdk.cortex_complete(
        model="claude-4-sonnet",
        messages=[{"role": "user", "content": f"We have {count} users"}]
    )
    
    return {"count": count, "summary": summary["choices"][0]["message"]["content"]}

await workflow()
`);
  console.log(`   Result: ${JSON.stringify(workflowResult.result)}`);
  console.log(`   Success: ${workflowResult.success}\n`);

  console.log("6. Measuring host call overhead...");
  const overheadResult = await runner.runPython(`
import time
iterations = 100
start = time.time()
for _ in range(iterations):
    await sdk.execute_query("SELECT 1")
elapsed = time.time() - start
{"iterations": iterations, "total_ms": elapsed * 1000, "avg_ms": (elapsed / iterations) * 1000}
`);
  const overhead = overheadResult.result;
  console.log(`   ${overhead.iterations} calls in ${overhead.total_ms?.toFixed(2)}ms`);
  console.log(`   Avg per call: ${overhead.avg_ms?.toFixed(3)}ms\n`);

  console.log("7. Testing warm instance pool...");
  const pool = new PyodidePool(2);
  pool.registerHostFunction("execute_query", async () => ({ rows: [] }));

  console.log("   Warming up 2 instances...");
  const warmupTimes = await pool.warmup(2);
  console.log(`   Warmup: ${warmupTimes.map((t) => t.toFixed(0) + "ms").join(", ")}\n`);

  const warmStart = performance.now();
  const warmRunner = await pool.acquire();
  const warmTime = performance.now() - warmStart;
  console.log(`   Warm acquire: ${warmTime.toFixed(2)}ms (target: <100ms)`);

  const quickResult = await warmRunner.runPython(`1 + 1`);
  console.log(`   Quick exec: ${quickResult.executionTimeMs.toFixed(2)}ms`);

  pool.release(warmRunner);
  console.log(`   Pool size: ${pool.size()}\n`);

  console.log("=== Summary ===");
  console.log(`Host functions: ${queryResult.success && llmResult.success ? "✓" : "✗"}`);
  console.log(`SDK workflow: ${workflowResult.success ? "✓" : "✗"}`);
  console.log(`Call overhead: ${overhead.avg_ms?.toFixed(3)}ms`);
  console.log(`Warm start: ${warmTime.toFixed(2)}ms`);

  const allPassed = queryResult.success && llmResult.success && workflowResult.success && warmTime < 100;
  process.exit(allPassed ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
