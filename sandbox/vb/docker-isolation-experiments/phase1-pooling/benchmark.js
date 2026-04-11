import Docker from 'dockerode';
import { ContainerPool } from './pool.js';

const docker = new Docker({ socketPath: '/var/run/docker.sock' });

const IMAGE = 'python:3.11-slim';
const ITERATIONS = 10;

async function ensureImage() {
  console.log(`Ensuring image ${IMAGE} is available...`);
  try {
    await docker.getImage(IMAGE).inspect();
    console.log('Image already pulled');
  } catch {
    console.log('Pulling image...');
    await new Promise((resolve, reject) => {
      docker.pull(IMAGE, (err, stream) => {
        if (err) return reject(err);
        docker.modem.followProgress(stream, (err) => {
          if (err) reject(err);
          else resolve();
        });
      });
    });
    console.log('Image pulled');
  }
}

async function benchmarkColdStart() {
  console.log('\n=== COLD START BENCHMARK ===');
  console.log(`Running ${ITERATIONS} cold container starts...`);
  
  const times = [];
  
  for (let i = 0; i < ITERATIONS; i++) {
    const start = performance.now();
    
    const container = await docker.createContainer({
      Image: IMAGE,
      Cmd: ['python3', '-c', 'print("hello")'],
      HostConfig: {
        Memory: 128 * 1024 * 1024,
        NetworkMode: 'none',
      },
    });
    
    await container.start();
    await container.wait();
    
    const elapsed = performance.now() - start;
    times.push(elapsed);
    
    await container.remove({ force: true });
    
    process.stdout.write(`\r  Iteration ${i + 1}/${ITERATIONS}: ${elapsed.toFixed(0)}ms`);
  }
  
  console.log('\n');
  return times;
}

async function benchmarkWarmStart() {
  console.log('\n=== WARM START BENCHMARK (Pooled) ===');
  console.log(`Running ${ITERATIONS} warm container executions...`);
  
  const pool = new ContainerPool({
    image: IMAGE,
    minSize: 3,
    maxSize: 5,
  });
  
  await pool.initialize();
  
  const times = [];
  
  for (let i = 0; i < ITERATIONS; i++) {
    const start = performance.now();
    
    const entry = await pool.acquire();
    const result = await pool.executeInContainer(entry, 'python3 -c "print(\'hello\')"');
    await pool.release(entry);
    
    const elapsed = performance.now() - start;
    times.push(elapsed);
    
    process.stdout.write(`\r  Iteration ${i + 1}/${ITERATIONS}: ${elapsed.toFixed(0)}ms`);
  }
  
  console.log('\n');
  
  await pool.shutdown();
  return times;
}

function analyzeResults(name, times) {
  times.sort((a, b) => a - b);
  
  const mean = times.reduce((a, b) => a + b) / times.length;
  const median = times[Math.floor(times.length / 2)];
  const p95 = times[Math.floor(times.length * 0.95)];
  const min = times[0];
  const max = times[times.length - 1];
  
  console.log(`${name}:`);
  console.log(`  Mean:   ${mean.toFixed(1)}ms`);
  console.log(`  Median: ${median.toFixed(1)}ms`);
  console.log(`  P95:    ${p95.toFixed(1)}ms`);
  console.log(`  Min:    ${min.toFixed(1)}ms`);
  console.log(`  Max:    ${max.toFixed(1)}ms`);
  
  return { mean, median, p95, min, max };
}

async function main() {
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║   P67 Container Pool Benchmark                 ║');
  console.log('╚════════════════════════════════════════════════╝');
  
  await ensureImage();
  
  const coldTimes = await benchmarkColdStart();
  const warmTimes = await benchmarkWarmStart();
  
  console.log('\n=== RESULTS ===\n');
  
  const coldStats = analyzeResults('Cold Start (new container each time)', coldTimes);
  console.log('');
  const warmStats = analyzeResults('Warm Start (pooled containers)', warmTimes);
  
  console.log('\n=== IMPROVEMENT ===\n');
  const speedup = coldStats.mean / warmStats.mean;
  console.log(`  Speedup: ${speedup.toFixed(1)}x faster`);
  console.log(`  Latency reduction: ${(coldStats.mean - warmStats.mean).toFixed(0)}ms saved per execution`);
  
  // Save results
  const results = {
    timestamp: new Date().toISOString(),
    iterations: ITERATIONS,
    image: IMAGE,
    coldStart: coldStats,
    warmStart: warmStats,
    speedup,
  };
  
  const fs = await import('fs');
  const resultsPath = '../benchmarks/results/pooling-benchmark.json';
  fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${resultsPath}`);
}

main().catch(console.error);
