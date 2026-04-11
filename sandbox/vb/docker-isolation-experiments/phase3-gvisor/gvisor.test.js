import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';
import Docker from 'dockerode';

const docker = new Docker({ socketPath: '/var/run/docker.sock' });
const IMAGE = 'python:3.11-slim';

async function isGvisorAvailable() {
  const info = await docker.info();
  const runtimes = info.Runtimes || {};
  return 'runsc' in runtimes;
}

async function execInContainer(container, cmd) {
  const exec = await container.exec({
    Cmd: ['sh', '-c', cmd],
    AttachStdout: true,
    AttachStderr: true,
  });
  
  const stream = await exec.start({});
  
  return new Promise((resolve) => {
    const stdout = [];
    const stderr = [];
    docker.modem.demuxStream(stream, { write: c => stdout.push(c) }, { write: c => stderr.push(c) });
    stream.on('end', () => resolve({
      stdout: Buffer.concat(stdout).toString('utf8').trim(),
      stderr: Buffer.concat(stderr).toString('utf8').trim(),
    }));
  });
}

describe('gVisor Compatibility Tests', async () => {
  const gvisorAvailable = await isGvisorAvailable();
  
  if (!gvisorAvailable) {
    it.skip('gVisor not available - skipping tests', () => {});
    return;
  }

  let container;

  before(async () => {
    container = await docker.createContainer({
      Image: IMAGE,
      Cmd: ['sleep', 'infinity'],
      HostConfig: {
        Runtime: 'runsc',
        Memory: 128 * 1024 * 1024,
        CapDrop: ['ALL'],
        SecurityOpt: ['no-new-privileges:true'],
        NetworkMode: 'none',
        Tmpfs: { '/tmp': 'rw,noexec,nosuid,size=64m' },
      },
    });
    await container.start();
  });

  after(async () => {
    if (container) {
      await container.stop({ t: 1 }).catch(() => {});
      await container.remove({ force: true }).catch(() => {});
    }
  });

  it('runs basic Python code', async () => {
    const result = await execInContainer(container, 'python3 -c "print(1 + 1)"');
    assert.strictEqual(result.stdout, '2');
  });

  it('supports json module', async () => {
    const result = await execInContainer(container, 'python3 -c "import json; print(json.dumps({\'a\': 1}))"');
    assert.strictEqual(result.stdout, '{"a": 1}');
  });

  it('supports subprocess', async () => {
    const result = await execInContainer(container, 
      'python3 -c "import subprocess; print(subprocess.run([\'echo\', \'test\'], capture_output=True).stdout.decode().strip())"'
    );
    assert.strictEqual(result.stdout, 'test');
  });

  it('supports file I/O in /tmp', async () => {
    const result = await execInContainer(container, 
      'python3 -c "open(\'/tmp/test.txt\', \'w\').write(\'hello\'); print(open(\'/tmp/test.txt\').read())"'
    );
    assert.strictEqual(result.stdout, 'hello');
  });

  it('supports time module', async () => {
    const result = await execInContainer(container, 
      'python3 -c "import time; start=time.time(); time.sleep(0.1); print(round(time.time()-start, 1))"'
    );
    assert.ok(parseFloat(result.stdout) >= 0.1);
  });

  it('supports threading', async () => {
    const code = `
import threading
import json

results = []
def worker(n):
    results.append(n * 2)

threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()
print(json.dumps(sorted(results)))
`;
    const result = await execInContainer(container, `python3 -c '${code}'`);
    assert.deepStrictEqual(JSON.parse(result.stdout), [0, 2, 4, 6, 8]);
  });

  it('executes simulated LangGraph workflow', async () => {
    const workflowCode = `
import json

def run_workflow(data):
    state = {"step": 0, "nodes_executed": []}
    
    # Node 1: Input parser
    state["step"] = 1
    state["nodes_executed"].append("parser")
    state["input"] = data
    
    # Node 2: Processor
    state["step"] = 2
    state["nodes_executed"].append("processor")
    state["result"] = len(data.get("query", "")) * 2
    
    # Node 3: Output formatter
    state["step"] = 3
    state["nodes_executed"].append("formatter")
    state["output"] = {"answer": state["result"]}
    
    return state

result = run_workflow({"query": "test query"})
print(json.dumps(result))
`;
    
    const codeB64 = Buffer.from(workflowCode).toString('base64');
    await execInContainer(container, `echo "${codeB64}" | base64 -d > /tmp/workflow.py`);
    
    const result = await execInContainer(container, 'python3 /tmp/workflow.py');
    const output = JSON.parse(result.stdout);
    
    assert.strictEqual(output.step, 3);
    assert.strictEqual(output.result, 20);
    assert.deepStrictEqual(output.nodes_executed, ['parser', 'processor', 'formatter']);
  });
});
