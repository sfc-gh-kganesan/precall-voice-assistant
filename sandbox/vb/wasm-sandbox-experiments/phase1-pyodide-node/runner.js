import { loadPyodide } from "pyodide";

export class PyodideRunner {
  constructor() {
    this.pyodide = null;
    this.initTimeMs = 0;
    this.hostFunctions = new Map();
    this.stdout = [];
    this.stderr = [];
  }

  async initialize() {
    const start = performance.now();

    this.pyodide = await loadPyodide();

    this.initTimeMs = performance.now() - start;

    await this.setupHostBridge();

    return this.initTimeMs;
  }

  async setupHostBridge() {
    if (!this.pyodide) throw new Error("Pyodide not initialized");

    const self = this;

    const hostCall = async (methodJson) => {
      const request = JSON.parse(methodJson);
      const handler = self.hostFunctions.get(request.method);

      if (!handler) {
        return JSON.stringify({
          success: false,
          error: `Unknown method: ${request.method}`,
        });
      }

      try {
        const result = await handler(request.params || {});
        return JSON.stringify({ success: true, result });
      } catch (e) {
        return JSON.stringify({
          success: false,
          error: e instanceof Error ? e.message : String(e),
        });
      }
    };

    this.pyodide.globals.set("_p67_host_call_js", hostCall);

    await this.pyodide.runPythonAsync(`
import json
import sys
from io import StringIO

class P67SDK:
    """Mock P67 SDK that calls host functions."""
    
    def __init__(self):
        self._params = {}
    
    def set_parameters(self, params):
        self._params = params
    
    def get_parameters(self):
        return self._params
    
    async def _call_host(self, method, **params):
        request = json.dumps({"method": method, "params": params})
        response_json = await _p67_host_call_js(request)
        response = json.loads(response_json)
        if not response.get("success"):
            raise Exception(response.get("error", "Unknown error"))
        return response.get("result")
    
    async def execute_query(self, sql, binds=None):
        return await self._call_host("execute_query", sql=sql, binds=binds or [])
    
    async def cortex_complete(self, model, messages, **kwargs):
        return await self._call_host("cortex_complete", model=model, messages=messages, **kwargs)
    
    async def http_request(self, url, method="GET", **kwargs):
        return await self._call_host("http_request", url=url, method=method, **kwargs)
    
    async def close(self):
        pass

sdk = P67SDK()
`);
  }

  registerHostFunction(name, handler) {
    this.hostFunctions.set(name, handler);
  }

  async runPython(code) {
    if (!this.pyodide) throw new Error("Pyodide not initialized");

    const start = performance.now();

    try {
      const result = await this.pyodide.runPythonAsync(code);
      const executionTimeMs = performance.now() - start;

      let jsResult = result;
      if (result && typeof result.toJs === "function") {
        jsResult = result.toJs({ dict_converter: Object.fromEntries });
      }

      return {
        success: true,
        result: jsResult,
        executionTimeMs,
      };
    } catch (e) {
      const executionTimeMs = performance.now() - start;
      return {
        success: false,
        executionTimeMs,
        error: e instanceof Error ? e.message : String(e),
      };
    }
  }

  async installPackages(packages) {
    if (!this.pyodide) throw new Error("Pyodide not initialized");
    await this.pyodide.loadPackage("micropip");
    const micropip = this.pyodide.pyimport("micropip");

    for (const pkg of packages) {
      console.log(`Installing ${pkg}...`);
      await micropip.install(pkg);
    }
  }

  getInitTimeMs() {
    return this.initTimeMs;
  }

  isInitialized() {
    return this.pyodide !== null;
  }
}

export class PyodidePool {
  constructor(maxSize = 5) {
    this.pool = [];
    this.maxSize = maxSize;
    this.hostFunctions = new Map();
  }

  registerHostFunction(name, handler) {
    this.hostFunctions.set(name, handler);
  }

  async warmup(count = 1) {
    const times = [];
    for (let i = 0; i < Math.min(count, this.maxSize); i++) {
      const runner = new PyodideRunner();

      for (const [name, handler] of this.hostFunctions) {
        runner.registerHostFunction(name, handler);
      }

      const initTime = await runner.initialize();
      times.push(initTime);
      this.pool.push(runner);
    }
    return times;
  }

  async acquire() {
    if (this.pool.length > 0) {
      return this.pool.pop();
    }

    const runner = new PyodideRunner();
    for (const [name, handler] of this.hostFunctions) {
      runner.registerHostFunction(name, handler);
    }
    await runner.initialize();
    return runner;
  }

  release(runner) {
    if (this.pool.length < this.maxSize) {
      this.pool.push(runner);
    }
  }

  size() {
    return this.pool.length;
  }
}
