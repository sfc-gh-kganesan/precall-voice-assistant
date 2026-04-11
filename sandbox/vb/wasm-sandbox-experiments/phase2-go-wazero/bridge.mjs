// Node.js IPC Bridge for Go ↔ Pyodide communication
// This script runs as a subprocess managed by Go

import { loadPyodide } from "pyodide";
import * as readline from "readline";

let pyodide = null;
let pendingHostCalls = new Map();
let callId = 0;

async function initialize() {
  console.error("[Node] Loading Pyodide...");
  pyodide = await loadPyodide();
  await pyodide.loadPackage("micropip");
  
  // Install LangGraph
  await pyodide.runPythonAsync(`
import micropip
await micropip.install('langgraph==0.0.38')
  `);
  
  // Set up host function bridge in Python
  await pyodide.runPythonAsync(`
import json
import sys

# Host call registry - will be populated by bridge
_pending_results = {}
_call_id = 0

def _host_call(name, **kwargs):
    """Call a host function and wait for result"""
    global _call_id
    _call_id += 1
    call_id = str(_call_id)
    
    # Send request to Go via stdout
    request = json.dumps({
        "type": "host_call",
        "id": call_id,
        "name": name,
        "args": kwargs
    })
    print(request, flush=True)
    
    # Result will be injected by the bridge
    # For now, return a placeholder that will be replaced
    return {"__pending_call_id": call_id}

# P67 SDK functions
def execute_query(sql):
    """Execute a SQL query via Snowflake"""
    return _host_call("execute_query", sql=sql)

def cortex_complete(prompt, model="snowflake-arctic"):
    """Call Cortex Complete API"""
    return _host_call("cortex_complete", prompt=prompt, model=model)

def http_request(url, method="GET", body=None, headers=None):
    """Make an HTTP request"""
    return _host_call("http_request", url=url, method=method, body=body, headers=headers)

def interrupt(message):
    """Interrupt workflow for human approval"""
    return _host_call("interrupt", message=message)
  `);
  
  console.error("[Node] Pyodide ready with LangGraph");
  
  // Signal ready to Go
  sendMessage({ type: "ready" });
}

function sendMessage(msg) {
  console.log(JSON.stringify(msg));
}

async function handleMessage(line) {
  let msg;
  try {
    msg = JSON.parse(line);
  } catch (e) {
    return; // Ignore non-JSON input
  }
  
  switch (msg.type) {
    case "execute":
      try {
        // Execute the workflow code
        const result = await pyodide.runPythonAsync(msg.code);
        
        // Convert Python result to JS
        let jsResult;
        try {
          jsResult = result?.toJs ? result.toJs({ dict_converter: Object.fromEntries }) : result;
        } catch {
          jsResult = String(result);
        }
        
        sendMessage({ type: "result", result: jsResult });
      } catch (error) {
        sendMessage({ type: "error", error: error.message });
      }
      break;
      
    case "host_result":
      // Inject result back into Python for pending host call
      if (pendingHostCalls.has(msg.id)) {
        const resolve = pendingHostCalls.get(msg.id);
        pendingHostCalls.delete(msg.id);
        if (msg.error) {
          resolve({ error: msg.error });
        } else {
          resolve(msg.result);
        }
      }
      break;
  }
}

// Set up readline for IPC with Go
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on("line", handleMessage);

// Initialize Pyodide
initialize().catch(err => {
  console.error("[Node] Initialization failed:", err);
  process.exit(1);
});
