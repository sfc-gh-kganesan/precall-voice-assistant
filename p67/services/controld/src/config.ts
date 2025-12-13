import { mkdtempSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { tmpdir } from 'os';
import { fileURLToPath } from 'url';
import { config as dotenvConfig } from 'dotenv';

dotenvConfig();

function createTempDir() {
  return mkdtempSync(join(tmpdir(), 'p67-controld-'));
}

export type ServerConfig = {
  port: number;
  nodeEnv: string;
  localStoragePath: string;
};

export const loadConfig = (): ServerConfig => {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);
  return {
    port: parseInt(process.env.PORT || '3002'),
    nodeEnv: process.env.NODE_ENV || 'development',
    localStoragePath: resolve(__dirname, process.env.DATA_ROOT || createTempDir()),
  };
};
