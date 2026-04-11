import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';
import { ContainerPool } from './pool.js';

describe('ContainerPool', () => {
  let pool;

  after(async () => {
    if (pool) {
      await pool.shutdown();
    }
  });

  it('initializes with minimum containers', async () => {
    pool = new ContainerPool({
      image: 'python:3.11-slim',
      minSize: 2,
      maxSize: 4,
    });

    await pool.initialize();
    
    const stats = pool.getStats();
    assert.strictEqual(stats.poolSize, 2);
    assert.strictEqual(stats.inUse, 0);
    assert.strictEqual(stats.total, 2);
  });

  it('acquires container from pool (warm)', async () => {
    const startTime = Date.now();
    const entry = await pool.acquire();
    const elapsed = Date.now() - startTime;
    
    assert.ok(entry.container);
    assert.ok(entry.id);
    assert.ok(elapsed < 100, `Warm acquire took ${elapsed}ms, expected <100ms`);
    
    const stats = pool.getStats();
    assert.strictEqual(stats.inUse, 1);
    
    await pool.release(entry);
  });

  it('executes command in container', async () => {
    const entry = await pool.acquire();
    
    const result = await pool.executeInContainer(entry, 'python3 -c "print(1 + 1)"');
    assert.strictEqual(result.stdout.trim(), '2');
    
    await pool.release(entry);
  });

  it('releases and reuses containers', async () => {
    const entry1 = await pool.acquire();
    const id1 = entry1.id;
    await pool.release(entry1);
    
    const entry2 = await pool.acquire();
    assert.strictEqual(entry2.id, id1, 'Should reuse same container');
    await pool.release(entry2);
  });

  it('creates new container when pool exhausted', async () => {
    const entries = [];
    
    // Acquire all pooled containers
    const initialStats = pool.getStats();
    for (let i = 0; i < initialStats.poolSize; i++) {
      entries.push(await pool.acquire());
    }
    
    // Next acquire should create new
    const newEntry = await pool.acquire();
    assert.ok(newEntry);
    entries.push(newEntry);
    
    // Release all
    for (const entry of entries) {
      await pool.release(entry);
    }
  });

  it('throws when max capacity reached', async () => {
    pool = new ContainerPool({
      image: 'python:3.11-slim',
      minSize: 1,
      maxSize: 2,
    });
    await pool.initialize();

    const entries = [];
    
    // Fill to max
    entries.push(await pool.acquire());
    entries.push(await pool.acquire());
    
    // Next should throw
    await assert.rejects(
      async () => pool.acquire(),
      { message: 'Pool exhausted: max containers in use' }
    );

    // Cleanup
    for (const entry of entries) {
      await pool.release(entry);
    }
  });

  it('runs Python workflow simulation', async () => {
    pool = new ContainerPool({
      image: 'python:3.11-slim',
      minSize: 2,
      maxSize: 4,
    });
    await pool.initialize();

    const entry = await pool.acquire();
    
    const pythonCode = `
import json
state = {"counter": 0}
for i in range(5):
    state["counter"] += 1
print(json.dumps(state))
`;
    
    const result = await pool.executeInContainer(
      entry,
      `python3 -c '${pythonCode.replace(/'/g, "'\"'\"'")}'`
    );
    
    const output = JSON.parse(result.stdout.trim());
    assert.strictEqual(output.counter, 5);
    
    await pool.release(entry);
  });
});
