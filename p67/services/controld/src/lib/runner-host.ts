import { ExecuteMessage } from './runner.js';
import { z } from 'zod';
import * as path from 'path';
import * as fs from 'fs';
import { AgentSDK, P67Config, P67ConfigValue } from '@p67/agent-sdk';
import yaml from 'yaml';
import { parseManifest, Manifest } from './manifest';

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

function validateConfig(config: P67ConfigValue): P67ConfigValue {
  // Patch config and fix accessURL if it's missing
  if (!config.accessUrl) {
    if (config.account) {
      const accountLocator = config.account.replaceAll('_', '-').toLowerCase();
      config.accessUrl = `https://${accountLocator}.snowflakecomputing.com`;
    }
  }

  // Determine and set authenticator as appropriate
  if (!config.authenticator) {
    if (config.token) {
      config.authenticator = 'PROGRAMMATIC_ACCESS_TOKEN';
    } else if (config.password) {
      config.authenticator = 'PASSWORD';
    }
  }

  if (config.authenticator === 'PROGRAMMATIC_ACCESS_TOKEN' && !config.token) {
    throw new Error('SNOWFLAKE_TOKEN is required for PROGRAMMATIC_ACCESS_TOKEN authenticator');
  }
  if (config.authenticator === 'PASSWORD' && !config.password) {
    throw new Error('SNOWFLAKE_PASSWORD is required for PASSWORD authenticator');
  }
  if (config.token && config.password) {
    throw new Error(
      'Both "token" and "password" are set in config; only one authentication method can be used.',
    );
  }

  return config;
}

function hydrateConfig(manifest: Manifest): P67Config {
  const config = new Map<string, P67ConfigValue>();
  for (const c of manifest.config) {
    const validated = validateConfig({
      account: c.account,
      username: c.username,
      authenticator: c.authenticator,
      accessUrl: c.accessUrl,
      token: c.token,
      password: c.password,
      warehouse: c.warehouse,
      database: c.database,
      schema: c.schema,
    });
    config.set(c.config_name, validated);
  }

  return { snowflakeConfig: config };
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

    const config = hydrateConfig(manifest);
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
