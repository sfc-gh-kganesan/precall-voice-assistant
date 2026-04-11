import Docker from 'dockerode';
import { EventEmitter } from 'events';

const docker = new Docker({ socketPath: '/var/run/docker.sock' });

export class ContainerPool extends EventEmitter {
  constructor(options = {}) {
    super();
    this.image = options.image || 'python:3.11-slim';
    this.minSize = options.minSize || 2;
    this.maxSize = options.maxSize || 10;
    this.idleTimeoutMs = options.idleTimeoutMs || 300000; // 5 min
    this.pool = [];
    this.inUse = new Set();
    this.starting = false;
  }

  async initialize() {
    console.log(`[Pool] Initializing with ${this.minSize} warm containers...`);
    const startTime = Date.now();
    
    const promises = [];
    for (let i = 0; i < this.minSize; i++) {
      promises.push(this._createWarmContainer());
    }
    
    await Promise.all(promises);
    console.log(`[Pool] Initialized ${this.pool.length} containers in ${Date.now() - startTime}ms`);
  }

  async _createWarmContainer() {
    const container = await docker.createContainer({
      Image: this.image,
      Cmd: ['sleep', 'infinity'], // Keep alive
      Tty: false,
      OpenStdin: true,
      HostConfig: {
        Memory: 128 * 1024 * 1024, // 128MB
        NanoCpus: 500_000_000,     // 0.5 CPU
        NetworkMode: 'none',
        ReadonlyRootfs: false,     // Need writable for workflow
        CapDrop: ['ALL'],
        SecurityOpt: ['no-new-privileges:true'],
        Tmpfs: { '/tmp': 'rw,noexec,nosuid,size=64m' },
      },
      Labels: {
        'p67.pool': 'true',
        'p67.created': Date.now().toString(),
      },
    });

    await container.start();
    
    const entry = {
      container,
      id: container.id.slice(0, 12),
      createdAt: Date.now(),
      lastUsed: Date.now(),
    };
    
    this.pool.push(entry);
    this.emit('container:created', entry.id);
    return entry;
  }

  async acquire() {
    const startTime = Date.now();
    
    // Try to get from pool
    if (this.pool.length > 0) {
      const entry = this.pool.pop();
      entry.lastUsed = Date.now();
      this.inUse.add(entry.id);
      
      const acquireTime = Date.now() - startTime;
      this.emit('container:acquired', { id: entry.id, warm: true, timeMs: acquireTime });
      return entry;
    }

    // Pool empty - create new if under max
    if (this.inUse.size < this.maxSize) {
      const entry = await this._createWarmContainer();
      this.pool.pop(); // Remove from pool (we're using it immediately)
      this.inUse.add(entry.id);
      
      const acquireTime = Date.now() - startTime;
      this.emit('container:acquired', { id: entry.id, warm: false, timeMs: acquireTime });
      return entry;
    }

    // At max capacity - wait or throw
    throw new Error('Pool exhausted: max containers in use');
  }

  async release(entry, options = {}) {
    const { destroy = false } = options;
    
    this.inUse.delete(entry.id);

    if (destroy) {
      await this._destroyContainer(entry);
      return;
    }

    // Reset container state for reuse
    try {
      // Execute cleanup script
      const exec = await entry.container.exec({
        Cmd: ['sh', '-c', 'rm -rf /workflow/* 2>/dev/null; true'],
        AttachStdout: true,
        AttachStderr: true,
      });
      await exec.start({ Detach: true });
      
      entry.lastUsed = Date.now();
      this.pool.push(entry);
      this.emit('container:released', entry.id);
    } catch (err) {
      console.error(`[Pool] Failed to reset container ${entry.id}:`, err.message);
      await this._destroyContainer(entry);
    }

    // Replenish pool if below minimum
    this._maintainMinSize();
  }

  async _destroyContainer(entry) {
    try {
      await entry.container.stop({ t: 1 });
    } catch (e) {
      // Ignore - might already be stopped
    }
    
    try {
      await entry.container.remove({ force: true });
      this.emit('container:destroyed', entry.id);
    } catch (e) {
      if (e.statusCode !== 404) {
        console.error(`[Pool] Failed to remove container ${entry.id}:`, e.message);
      }
    }
  }

  async _maintainMinSize() {
    if (this.starting) return;
    
    const deficit = this.minSize - this.pool.length;
    if (deficit <= 0) return;

    this.starting = true;
    try {
      for (let i = 0; i < deficit; i++) {
        await this._createWarmContainer();
      }
    } finally {
      this.starting = false;
    }
  }

  async executeInContainer(entry, command) {
    const exec = await entry.container.exec({
      Cmd: ['sh', '-c', command],
      AttachStdout: true,
      AttachStderr: true,
    });

    const stream = await exec.start({});
    
    return new Promise((resolve, reject) => {
      const stdoutChunks = [];
      const stderrChunks = [];

      docker.modem.demuxStream(
        stream,
        { write: (c) => stdoutChunks.push(c) },
        { write: (c) => stderrChunks.push(c) }
      );

      stream.on('end', () => {
        resolve({
          stdout: Buffer.concat(stdoutChunks).toString('utf8'),
          stderr: Buffer.concat(stderrChunks).toString('utf8'),
        });
      });

      stream.on('error', reject);
    });
  }

  async shutdown() {
    console.log(`[Pool] Shutting down ${this.pool.length + this.inUse.size} containers...`);
    
    const allEntries = [...this.pool];
    this.pool = [];

    await Promise.all(allEntries.map(entry => this._destroyContainer(entry)));
    
    console.log('[Pool] Shutdown complete');
  }

  getStats() {
    return {
      poolSize: this.pool.length,
      inUse: this.inUse.size,
      total: this.pool.length + this.inUse.size,
      minSize: this.minSize,
      maxSize: this.maxSize,
    };
  }
}

export default ContainerPool;
