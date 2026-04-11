import Docker from 'dockerode';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const docker = new Docker({ socketPath: '/var/run/docker.sock' });

const IMAGE = 'python:3.11-slim';
const ITERATIONS = 10;

const RUNTIMES = {
  runc: {
    name: 'runc (default)',
    runtime: 'runc',
  },
  runsc: {
    name: 'gVisor (runsc)',
    runtime: 'runsc',
  },
};

const HARDENED_CONFIG = {
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
};

async function checkRuntimeAvailable(runtime) {
  const info = await docker.info();
  const runtimes = info.Runtimes || {};
  return runtime in runtimes || runtime === 'runc';
}

async function runBenchmark(runtimeKey, runtimeConfig) {
  const times = { coldStart: [], warmExec: [] };
  
  console.log(`\n--- ${runtimeConfig.name} ---`);
  
  console.log(`Cold start (${ITERATIONS} iterations):`);
  for (let i = 0; i < ITERATIONS; i++) {
    const start = performance.now();
    
    const container = await docker.createContainer({
      Image: IMAGE,
      Cmd: ['python3', '-c', 'print("hello")'],
      HostConfig: {
        ...HARDENED_CONFIG,
        Runtime: runtimeConfig.runtime,
      },
    });
    
    await container.start();
    await container.wait();
    
    const elapsed = performance.now() - start;
    times.coldStart.push(elapsed);
    
    await container.remove({ force: true });
    process.stdout.write(`\r  Iteration ${i + 1}/${ITERATIONS}: ${elapsed.toFixed(0)}ms`);
  }
  console.log('');

  console.log(`Warm exec (${ITERATIONS} iterations):`);
  const poolContainer = await docker.createContainer({
    Image: IMAGE,
    Cmd: ['sleep', 'infinity'],
    HostConfig: {
      ...HARDENED_CONFIG,
      Runtime: runtimeConfig.runtime,
    },
  });
  await poolContainer.start();

  for (let i = 0; i < ITERATIONS; i++) {
    const start = performance.now();
    
    const exec = await poolContainer.exec({
      Cmd: ['python3', '-c', 'print("hello")'],
      AttachStdout: true,
      AttachStderr: true,
    });
    
    const stream = await exec.start({});
    await new Promise((resolve) => {
      stream.on('end', resolve);
      stream.resume();
    });
    
    const elapsed = performance.now() - start;
    times.warmExec.push(elapsed);
    
    process.stdout.write(`\r  Iteration ${i + 1}/${ITERATIONS}: ${elapsed.toFixed(0)}ms`);
  }
  console.log('');

  await poolContainer.stop({ t: 1 }).catch(() => {});
  await poolContainer.remove({ force: true });
  
  return times;
}

function analyzeResults(times) {
  const analyze = (arr) => {
    arr.sort((a, b) => a - b);
    return {
      mean: arr.reduce((a, b) => a + b) / arr.length,
      median: arr[Math.floor(arr.length / 2)],
      p95: arr[Math.floor(arr.length * 0.95)],
      min: arr[0],
      max: arr[arr.length - 1],
    };
  };
  
  return {
    coldStart: analyze(times.coldStart),
    warmExec: analyze(times.warmExec),
  };
}

async function runWorkflowTest(runtime) {
  console.log(`\nWorkflow test (${runtime}):`);
  
  const container = await docker.createContainer({
    Image: IMAGE,
    Cmd: ['sleep', 'infinity'],
    HostConfig: {
      ...HARDENED_CONFIG,
      Runtime: runtime,
    },
  });
  
  await container.start();
  
  const workflowCode = `
import json
import time

def workflow(input_data):
    state = {"step": 0, "messages": []}
    
    state["step"] = 1
    state["messages"].append("Start")
    
    state["step"] = 2
    time.sleep(0.05)
    state["result"] = len(input_data.get("query", "")) * 2
    state["messages"].append("Processed")
    
    state["step"] = 3
    state["messages"].append("Done")
    
    return state

result = workflow({"query": "test input"})
print(json.dumps(result))
`;
  
  const codeB64 = Buffer.from(workflowCode).toString('base64');
  
  const setupExec = await container.exec({
    Cmd: ['sh', '-c', `echo "${codeB64}" | base64 -d > /tmp/workflow.py`],
    AttachStdout: true,
  });
  await setupExec.start({});
  
  const start = performance.now();
  const runExec = await container.exec({
    Cmd: ['python3', '/tmp/workflow.py'],
    AttachStdout: true,
    AttachStderr: true,
  });
  
  const stream = await runExec.start({});
  const output = await new Promise((resolve) => {
    const chunks = [];
    docker.modem.demuxStream(stream, { write: c => chunks.push(c) }, { write: () => {} });
    stream.on('end', () => resolve(Buffer.concat(chunks).toString('utf8').trim()));
  });
  
  const elapsed = performance.now() - start;
  
  await container.stop({ t: 1 }).catch(() => {});
  await container.remove({ force: true });
  
  try {
    const result = JSON.parse(output);
    console.log(`  ✓ Workflow completed in ${elapsed.toFixed(0)}ms`);
    console.log(`  Result: step=${result.step}, messages=${result.messages.length}`);
    return { success: true, elapsed, result };
  } catch (e) {
    console.log(`  ✗ Workflow failed: ${output}`);
    return { success: false, elapsed, error: output };
  }
}

async function main() {
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║   P67 gVisor vs runc Benchmark                 ║');
  console.log('╚════════════════════════════════════════════════╝');

  const info = await docker.info();
  console.log(`\nSystem: ${info.OperatingSystem} (${info.Architecture})`);
  
  const availableRuntimes = {};
  
  for (const [key, config] of Object.entries(RUNTIMES)) {
    const available = await checkRuntimeAvailable(config.runtime);
    if (available) {
      availableRuntimes[key] = config;
      console.log(`✓ ${config.name} available`);
    } else {
      console.log(`✗ ${config.name} NOT available`);
    }
  }
  
  if (Object.keys(availableRuntimes).length === 0) {
    console.log('\nNo runtimes available. Exiting.');
    process.exit(1);
  }

  const results = {};
  
  for (const [key, config] of Object.entries(availableRuntimes)) {
    const times = await runBenchmark(key, config);
    results[key] = analyzeResults(times);
    results[key].workflow = await runWorkflowTest(config.runtime);
  }

  console.log('\n╔════════════════════════════════════════════════╗');
  console.log('║   RESULTS SUMMARY                              ║');
  console.log('╚════════════════════════════════════════════════╝\n');
  
  console.log('Cold Start Latency:');
  console.log('| Runtime | Mean | Median | P95 |');
  console.log('|---------|------|--------|-----|');
  for (const [key, stats] of Object.entries(results)) {
    const s = stats.coldStart;
    console.log(`| ${RUNTIMES[key].name.padEnd(20)} | ${s.mean.toFixed(0).padStart(4)}ms | ${s.median.toFixed(0).padStart(4)}ms | ${s.p95.toFixed(0).padStart(3)}ms |`);
  }
  
  console.log('\nWarm Exec Latency (pooled):');
  console.log('| Runtime | Mean | Median | P95 |');
  console.log('|---------|------|--------|-----|');
  for (const [key, stats] of Object.entries(results)) {
    const s = stats.warmExec;
    console.log(`| ${RUNTIMES[key].name.padEnd(20)} | ${s.mean.toFixed(0).padStart(4)}ms | ${s.median.toFixed(0).padStart(4)}ms | ${s.p95.toFixed(0).padStart(3)}ms |`);
  }

  if (results.runc && results.runsc) {
    console.log('\nOverhead (gVisor vs runc):');
    const coldOverhead = ((results.runsc.coldStart.mean - results.runc.coldStart.mean) / results.runc.coldStart.mean * 100).toFixed(1);
    const warmOverhead = ((results.runsc.warmExec.mean - results.runc.warmExec.mean) / results.runc.warmExec.mean * 100).toFixed(1);
    console.log(`  Cold start: ${coldOverhead > 0 ? '+' : ''}${coldOverhead}%`);
    console.log(`  Warm exec:  ${warmOverhead > 0 ? '+' : ''}${warmOverhead}%`);
  }

  const outputPath = path.join(__dirname, '..', 'benchmarks', 'results', 'gvisor-benchmark.json');
  fs.writeFileSync(outputPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    system: {
      os: info.OperatingSystem,
      kernel: info.KernelVersion,
      arch: info.Architecture,
    },
    iterations: ITERATIONS,
    results,
  }, null, 2));
  
  console.log(`\nResults saved to ${outputPath}`);
}

main().catch(console.error);
