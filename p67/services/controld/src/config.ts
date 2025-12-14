import { mkdtempSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { tmpdir } from 'os';
import { fileURLToPath } from 'url';
import { config as dotenvConfig } from 'dotenv';

dotenvConfig();

function createTempDir() {
  return mkdtempSync(join(tmpdir(), 'p67-controld-'));
}

export type OAuthConfig = {
  google: {
    clientId: string;
    clientSecret: string;
    redirectUri: string;
  };
};

export type ServerConfig = {
  port: number;
  nodeEnv: string;
  localStoragePath: string;
  oauth: OAuthConfig;
};

export const loadConfig = (): ServerConfig => {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);

  // Validate required OAuth env vars
  const googleClientId = process.env.GOOGLE_CLIENT_ID;
  const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET;

  if (!googleClientId || !googleClientSecret) {
    throw new Error('GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables are required');
  }

  return {
    port: parseInt(process.env.PORT || '3002'),
    nodeEnv: process.env.NODE_ENV || 'development',
    localStoragePath: resolve(__dirname, process.env.DATA_ROOT || createTempDir()),
    oauth: {
      google: {
        clientId: googleClientId,
        clientSecret: googleClientSecret,
        redirectUri:
          process.env.GOOGLE_REDIRECT_URI || 'http://localhost:3002/api/auth/google/callback',
      },
    },
  };
};
