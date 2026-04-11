import Docker from 'dockerode';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const docker = new Docker({ socketPath: '/var/run/docker.sock' });

const IMAGE = 'python:3.11-slim';
const ITERATIONS = 10;

const seccompProfile = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'seccomp-profile.json'), 'utf8')
);

const SECURITY_LEVELS = {
  baseline: {
    name: 'Baseline (no hardening)',
    config: {
      HostConfig: {
        Memory: 128 * 1024 * 1024,
      },
    },
  },
  
  level1: {
    name: 'Level 1: Standard',
    config: {
      HostConfig: {
        Memory: 128 * 1024 * 1024,
        CapDrop: ['ALL'],
        SecurityOpt: ['no-new-privileges:true'],
        NetworkMode: 'none',
      },
    },
  },
  
  level2: {
    name: 'Level 2: Hardened',
    config: {
      HostConfig: {
        Memory: 128 * 1024 * 1024,
        NanoCpus: 500_000_000,
        PidsLimit: 100,
        CapDrop: ['ALL'],
        SecurityOpt: [
          'no-new-privileges:true',
        ],
        ReadonlyRootfs: true,
        NetworkMode: 'none',
        Tmpfs: {
          '/tmp': 'rw,noexec,nosuid,size=64m',
          '/var/tmp': 'rw,noexec,nosuid,size=32m',
        },
      },
    },
  },

  level2_seccomp: {
    name: 'Level 2: Hardened + Seccomp',
    config: {
      HostConfig: {
        Memory: 128 * 1024 * 1024,
        NanoCpus: 500_000_000,
        PidsLimit: 100,
        CapDrop: ['ALL'],
        SecurityOpt: [
          'no-new-privileges:true',
          `seccomp=${JSON.stringify(seccompProfile)}`,
        ],
        ReadonlyRootfs: true,
        NetworkMode: 'none',
        Tmpfs: {
          '/tmp': 'rw,noexec,nosuid,size=64m',
          '/var/tmp': 'rw,noexec,nosuid,size=32m',
        },
      },
    },
  },
};

async function runBenchmark(levelName, levelConfig) {
  const times = [];
  
  for (let i = 0; i < ITERATIONS; i++) {
    const start = performance.now();
    
    const container = await docker.createContainer({
      Image: IMAGE,
      Cmd: ['python3', '-c', 'import json; print(json.dumps({"result": 42}))'],
      ...levelConfig.config,
    });
    
    await container.start();
    await container.wait();
    
    const elapsed = performance.now() - start;
    times.push(elapsed);
    
    await container.remove({ force: true });
    
    process.stdout.write(`\r  [${levelName}] ${i + 1}/${ITERATIONS}: ${elapsed.toFixed(0)}ms`);
  }
  
  console.log('');
  return times;
}

function analyzeResults(name, times) {
  times.sort((a, b) => a - b);
  
  const mean = times.reduce((a, b) => a + b) / times.length;
  const median = times[Math.floor(times.length / 2)];
  const p95 = times[Math.floor(times.length * 0.95)];
  const min = times[0];
  const max = times[times.length - 1];
  
  return { name, mean, median, p95, min, max };
}

async function testSecurityBlocking() {
  console.log('\n=== SECURITY BLOCKING TESTS ===\n');
  
  const tests = [
    {
      name: 'mount blocked',
      cmd: 'mount /dev/sda1 /mnt 2>&1 || echo "BLOCKED"',
      expectBlocked: true,
    },
    {
      name: 'network blocked (curl)',
      cmd: 'python3 -c "import urllib.request; urllib.request.urlopen(\'http://google.com\')" 2>&1 || echo "BLOCKED"',
      expectBlocked: true,
    },
    {
      name: 'process spawn works',
      cmd: 'python3 -c "import subprocess; print(subprocess.run([\'echo\', \'test\'], capture_output=True).stdout.decode().strip())"',
      expectBlocked: false,
    },
    {
      name: 'file write to /tmp works',
      cmd: 'python3 -c "open(\'/tmp/test.txt\', \'w\').write(\'hello\'); print(open(\'/tmp/test.txt\').read())"',
      expectBlocked: false,
    },
    {
      name: 'file write to / blocked (read-only)',
      cmd: 'touch /test.txt 2>&1 || echo "BLOCKED"',
      expectBlocked: true,
    },
  ];

  const container = await docker.createContainer({
    Image: IMAGE,
    Cmd: ['sleep', 'infinity'],
    ...SECURITY_LEVELS.level2.config,
  });
  
  await container.start();
  
  const results = [];
  
  for (const test of tests) {
    const exec = await container.exec({
      Cmd: ['sh', '-c', test.cmd],
      AttachStdout: true,
      AttachStderr: true,
    });
    
    const stream = await exec.start({});
    
    const output = await new Promise((resolve) => {
      const chunks = [];
      docker.modem.demuxStream(
        stream,
        { write: (c) => chunks.push(c) },
        { write: (c) => chunks.push(c) }
      );
      stream.on('end', () => resolve(Buffer.concat(chunks).toString('utf8').trim()));
    });
    
    const blocked = output.includes('BLOCKED') || output.includes('Permission denied') || output.includes('Network is unreachable');
    const pass = blocked === test.expectBlocked;
    
    results.push({ ...test, output: output.slice(0, 50), blocked, pass });
    console.log(`  ${pass ? '✓' : '✗'} ${test.name}: ${blocked ? 'BLOCKED' : 'ALLOWED'}`);
  }
  
  await container.stop({ t: 1 }).catch(() => {});
  await container.remove({ force: true });
  
  return results;
}

async function main() {
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║   P67 Security Hardening Benchmark             ║');
  console.log('╚════════════════════════════════════════════════╝\n');

  const allResults = {};
  
  console.log('=== PERFORMANCE OVERHEAD BY SECURITY LEVEL ===\n');
  
  for (const [key, level] of Object.entries(SECURITY_LEVELS)) {
    const times = await runBenchmark(key, level);
    allResults[key] = analyzeResults(level.name, times);
  }
  
  console.log('\n=== RESULTS SUMMARY ===\n');
  console.log('| Security Level | Mean | Median | P95 | Overhead |');
  console.log('|----------------|------|--------|-----|----------|');
  
  const baselineMean = allResults.baseline.mean;
  
  for (const [key, stats] of Object.entries(allResults)) {
    const overhead = ((stats.mean - baselineMean) / baselineMean * 100).toFixed(1);
    const overheadStr = key === 'baseline' ? '-' : `+${overhead}%`;
    console.log(`| ${stats.name.slice(0, 25).padEnd(25)} | ${stats.mean.toFixed(0).padStart(4)}ms | ${stats.median.toFixed(0).padStart(4)}ms | ${stats.p95.toFixed(0).padStart(3)}ms | ${overheadStr.padStart(8)} |`);
  }

  const securityResults = await testSecurityBlocking();
  
  const allPassed = securityResults.every(r => r.pass);
  console.log(`\nSecurity tests: ${allPassed ? '✓ ALL PASSED' : '✗ SOME FAILED'}`);

  const outputPath = path.join(__dirname, '..', 'benchmarks', 'results', 'hardening-benchmark.json');
  fs.writeFileSync(outputPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    iterations: ITERATIONS,
    performance: allResults,
    security: securityResults,
  }, null, 2));
  
  console.log(`\nResults saved to ${outputPath}`);
}

main().catch(console.error);
