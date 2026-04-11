import Docker from 'dockerode';
import { ContainerPool } from './pool.js';
import fs from 'fs';
import path from 'path';

const docker = new Docker({ socketPath: '/var/run/docker.sock' });

const WORKFLOW_CODE = `
import json
import sys
import time

def execute_workflow(input_data):
    """Simulated LangGraph-style workflow"""
    state = {"messages": [], "step": 0}
    
    # Node 1: Parse input
    state["step"] = 1
    state["input"] = input_data
    state["messages"].append(f"Step 1: Received input")
    
    # Node 2: Process (simulate LLM call delay)
    state["step"] = 2
    time.sleep(0.05)  # Simulate 50ms processing
    state["result"] = len(input_data.get("query", "")) * 2
    state["messages"].append(f"Step 2: Processed query")
    
    # Node 3: Format output
    state["step"] = 3
    state["output"] = {
        "answer": f"Result: {state['result']}",
        "steps": state["step"],
    }
    state["messages"].append(f"Step 3: Formatted output")
    
    return state

if __name__ == "__main__":
    input_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"query": "test"}
    result = execute_workflow(input_data)
    print(json.dumps(result))
`;

class WorkflowRunner {
  constructor(pool) {
    this.pool = pool;
  }

  async executeWorkflow(workflowCode, inputData) {
    const startTime = Date.now();
    const metrics = { acquireMs: 0, executeMs: 0, releaseMs: 0 };
    
    // Acquire container
    const acquireStart = Date.now();
    const entry = await this.pool.acquire();
    metrics.acquireMs = Date.now() - acquireStart;
    
    try {
      // Write workflow code to container
      const codeB64 = Buffer.from(workflowCode).toString('base64');
      await this.pool.executeInContainer(
        entry,
        `echo "${codeB64}" | base64 -d > /tmp/workflow.py`
      );
      
      // Execute workflow
      const inputJson = JSON.stringify(inputData).replace(/"/g, '\\"');
      const executeStart = Date.now();
      const result = await this.pool.executeInContainer(
        entry,
        `python3 /tmp/workflow.py "${inputJson}"`
      );
      metrics.executeMs = Date.now() - executeStart;
      
      if (result.stderr) {
        console.error('Workflow stderr:', result.stderr);
      }
      
      return {
        success: true,
        output: JSON.parse(result.stdout.trim()),
        metrics: {
          ...metrics,
          totalMs: Date.now() - startTime,
        },
      };
    } catch (err) {
      return {
        success: false,
        error: err.message,
        metrics: {
          ...metrics,
          totalMs: Date.now() - startTime,
        },
      };
    } finally {
      // Release container
      const releaseStart = Date.now();
      await this.pool.release(entry);
      metrics.releaseMs = Date.now() - releaseStart;
    }
  }
}

async function main() {
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║   P67 Workflow Execution Simulation            ║');
  console.log('╚════════════════════════════════════════════════╝\n');

  const pool = new ContainerPool({
    image: 'python:3.11-slim',
    minSize: 3,
    maxSize: 10,
  });

  console.log('Initializing container pool...');
  await pool.initialize();
  
  const runner = new WorkflowRunner(pool);
  
  const testCases = [
    { query: 'What is the weather?' },
    { query: 'Calculate the sum of 1 to 100' },
    { query: 'A longer query to test processing time with more characters' },
    { query: 'Short' },
    { query: 'Medium length query here' },
  ];

  console.log(`\nExecuting ${testCases.length} simulated workflows...\n`);
  
  const results = [];
  
  for (let i = 0; i < testCases.length; i++) {
    const input = testCases[i];
    console.log(`[${i + 1}/${testCases.length}] Running workflow with input: "${input.query.slice(0, 30)}..."`);
    
    const result = await runner.executeWorkflow(WORKFLOW_CODE, input);
    results.push(result);
    
    if (result.success) {
      console.log(`  ✓ Completed in ${result.metrics.totalMs}ms`);
      console.log(`    Acquire: ${result.metrics.acquireMs}ms | Execute: ${result.metrics.executeMs}ms`);
    } else {
      console.log(`  ✗ Failed: ${result.error}`);
    }
  }

  // Summary
  console.log('\n=== SUMMARY ===\n');
  
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  
  console.log(`Success: ${successful.length}/${results.length}`);
  
  if (successful.length > 0) {
    const totalTimes = successful.map(r => r.metrics.totalMs);
    const acquireTimes = successful.map(r => r.metrics.acquireMs);
    const executeTimes = successful.map(r => r.metrics.executeMs);
    
    const avg = arr => arr.reduce((a, b) => a + b, 0) / arr.length;
    
    console.log(`\nLatency (avg):`);
    console.log(`  Total:    ${avg(totalTimes).toFixed(1)}ms`);
    console.log(`  Acquire:  ${avg(acquireTimes).toFixed(1)}ms (container from pool)`);
    console.log(`  Execute:  ${avg(executeTimes).toFixed(1)}ms (workflow run)`);
    
    console.log(`\nPool Stats:`);
    const stats = pool.getStats();
    console.log(`  Pool size: ${stats.poolSize}`);
    console.log(`  In use: ${stats.inUse}`);
    console.log(`  Min/Max: ${stats.minSize}/${stats.maxSize}`);
  }

  await pool.shutdown();
  
  // Save results
  const resultsPath = path.join('..', 'benchmarks', 'results', 'workflow-simulation.json');
  fs.writeFileSync(resultsPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    testCases: testCases.length,
    results: results.map(r => ({
      success: r.success,
      metrics: r.metrics,
    })),
  }, null, 2));
  console.log(`\nResults saved to ${resultsPath}`);
}

main().catch(console.error);
