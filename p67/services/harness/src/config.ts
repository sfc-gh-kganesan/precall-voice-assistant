import { mkdtempSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { tmpdir } from 'os';
import { config as dotenvConfig } from 'dotenv';
import { fileURLToPath } from 'url';

dotenvConfig();

function createTempDir() {
  return mkdtempSync(join(tmpdir(), 'harness-'));
}

export type Config = {
  port: number;
  nodeEnv: string;
  localStoragePath: string;
};

export default function (): Config {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);

  return {
    port: parseInt(process.env.PORT || '3000'),
    nodeEnv: process.env.NODE_ENV || 'development',
    localStoragePath: resolve(__dirname, process.env.DATA_STORE || createTempDir()),
  };
}
