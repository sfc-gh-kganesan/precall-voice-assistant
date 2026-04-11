import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';
import Docker from 'dockerode';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const docker = new Docker({ socketPath: '/var/run/docker.sock' });
const IMAGE = 'python:3.11-slim';

const seccompProfile = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'seccomp-profile.json'), 'utf8')
);

const HARDENED_CONFIG = {
  Image: IMAGE,
  Cmd: ['sleep', 'infinity'],
  HostConfig: {
    Memory: 128 * 1024 * 1024,
    NanoCpus: 500_000_000,
    PidsLimit: 100,
    CapDrop: ['ALL'],
    SecurityOpt: ['no-new-privileges:true'],
    ReadonlyRootfs: true,
    NetworkMode: 'none',
    Tmpfs: {
      '/tmp': 'rw,noexec,nosuid,size=64m',
    },
  },
};

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
    docker.modem.demuxStream(
      stream,
      { write: (c) => stdout.push(c) },
      { write: (c) => stderr.push(c) }
    );
    stream.on('end', () => resolve({
      stdout: Buffer.concat(stdout).toString('utf8').trim(),
      stderr: Buffer.concat(stderr).toString('utf8').trim(),
    }));
  });
}

describe('Security Hardening', () => {
  let container;

  before(async () => {
    container = await docker.createContainer(HARDENED_CONFIG);
    await container.start();
  });

  after(async () => {
    if (container) {
      await container.stop({ t: 1 }).catch(() => {});
      await container.remove({ force: true }).catch(() => {});
    }
  });

  it('blocks write to root filesystem', async () => {
    const result = await execInContainer(container, 'touch /test.txt 2>&1; echo $?');
    assert.ok(
      result.stdout.includes('Read-only') || result.stdout.includes('1'),
      `Expected read-only error, got: ${result.stdout}`
    );
  });

  it('allows write to /tmp', async () => {
    const result = await execInContainer(container, 'echo "test" > /tmp/test.txt && cat /tmp/test.txt');
    assert.strictEqual(result.stdout, 'test');
  });

  it('blocks network access', async () => {
    const result = await execInContainer(
      container,
      'python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect((\'8.8.8.8\', 53))" 2>&1; echo "EXIT:$?"'
    );
    assert.ok(
      result.stdout.includes('Network is unreachable') || result.stdout.includes('EXIT:1'),
      `Expected network blocked, got: ${result.stdout}`
    );
  });

  it('runs Python code successfully', async () => {
    const result = await execInContainer(
      container,
      'python3 -c "import json; print(json.dumps({\'status\': \'ok\'}))"'
    );
    const output = JSON.parse(result.stdout);
    assert.strictEqual(output.status, 'ok');
  });

  it('allows subprocess spawn', async () => {
    const result = await execInContainer(
      container,
      'python3 -c "import subprocess; r = subprocess.run([\'echo\', \'hello\'], capture_output=True); print(r.stdout.decode().strip())"'
    );
    assert.strictEqual(result.stdout, 'hello');
  });

  it('enforces PID limit', async () => {
    const info = await container.inspect();
    assert.strictEqual(info.HostConfig.PidsLimit, 100);
  });

  it('enforces memory limit', async () => {
    const info = await container.inspect();
    assert.strictEqual(info.HostConfig.Memory, 128 * 1024 * 1024);
  });

  it('drops all capabilities', async () => {
    const info = await container.inspect();
    assert.deepStrictEqual(info.HostConfig.CapDrop, ['ALL']);
  });
});

describe('Workflow Execution Under Hardening', () => {
  let container;

  before(async () => {
    container = await docker.createContainer(HARDENED_CONFIG);
    await container.start();
  });

  after(async () => {
    if (container) {
      await container.stop({ t: 1 }).catch(() => {});
      await container.remove({ force: true }).catch(() => {});
    }
  });

  it('executes LangGraph-style workflow', async () => {
    const workflowCode = `
import json
import sys

def run_workflow(input_data):
    state = {"messages": [], "step": 0}
    
    # Simulated nodes
    state["step"] = 1
    state["messages"].append("Parsed input")
    
    state["step"] = 2
    state["result"] = len(input_data.get("query", "")) * 2
    state["messages"].append("Processed")
    
    state["step"] = 3
    state["output"] = {"answer": state["result"]}
    state["messages"].append("Complete")
    
    return state

input_data = json.loads(sys.argv[1])
result = run_workflow(input_data)
print(json.dumps(result))
`;
    
    const codeB64 = Buffer.from(workflowCode).toString('base64');
    await execInContainer(container, `echo "${codeB64}" | base64 -d > /tmp/workflow.py`);
    
    const result = await execInContainer(
      container,
      'python3 /tmp/workflow.py \'{"query": "test query"}\''
    );
    
    const output = JSON.parse(result.stdout);
    assert.strictEqual(output.step, 3);
    assert.strictEqual(output.result, 20); // "test query".length * 2
    assert.strictEqual(output.messages.length, 3);
  });

  it('handles JSON state correctly', async () => {
    const result = await execInContainer(
      container,
      `python3 -c "
import json
state = {'counter': 0, 'items': []}
for i in range(5):
    state['counter'] += 1
    state['items'].append(i)
print(json.dumps(state))
"`
    );
    
    const output = JSON.parse(result.stdout);
    assert.strictEqual(output.counter, 5);
    assert.deepStrictEqual(output.items, [0, 1, 2, 3, 4]);
  });
});
