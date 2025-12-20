import { ExecuteMessage } from './runner.js';
import { z } from 'zod';
import * as path from 'path';
import * as fs from 'fs';
import { AgentSDK, hydrateConfig } from './sdk';
import { parseManifest } from './manifest';
import { ValueManager } from './value-manager';

const ExecuteMessageSchema = z.object({
  dir: z.string(),
  action: z.literal('run'),
});

function error(err: Error | string) {
  process.send!({
    type: 'error',
    error: err instanceof Error ? err.message : String(error),
  });
}

process.on('message', async (message: ExecuteMessage) => {
  console.log(message);
  const m = ExecuteMessageSchema.safeParse(message);
  if (!m.success) {
    error(m.error);
    process.exit(1);
  }

  try {
    const scriptPath = path.resolve(m.data.dir, 'index.js');
    if (!fs.existsSync(scriptPath)) {
      throw new Error(`${scriptPath} does not exist, exiting.`);
    }

    console.log(`loading script ${scriptPath}`);
    const script = await import(scriptPath);
    console.log(`Loaded script!`);

    if (typeof script.main !== 'function') {
      throw new Error('Script does not export a main function');
    }

    const manifestStr = await fs.promises.readFile(
      path.resolve(m.data.dir, 'manifest.yaml'),
      'utf-8',
    );
    const manifest = parseManifest(manifestStr);

    // TODO: Use a real thing here.
    const valueManager = new ValueManager();

    const config = await hydrateConfig(manifest, valueManager);
    const sdk = new AgentSDK(config);

    const result = await script.main(sdk);

    process.send!({ type: 'result', data: result });
  } catch (error) {
    process.send!({
      type: 'error',
      error: error instanceof Error ? error.message : String(error),
    });
    process.exit(1);
  }

  process.exit(0);
});
