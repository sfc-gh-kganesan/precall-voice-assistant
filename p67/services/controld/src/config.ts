import { readFileSync, existsSync, mkdtempSync } from 'fs';
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
  database: {
    url: string;
  };
};

function readFileIfExistsSync(filePath: string): string | null {
  if (!existsSync(filePath)) {
    return null;
  }

  return readFileSync(filePath, 'utf-8');
}

export const loadConfig = (): ServerConfig => {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);

  // Validate required OAuth env vars
  const googleClientId =
    readFileIfExistsSync('/opt/creds/google_oauth_client_id/secret_string') ??
    process.env.GOOGLE_CLIENT_ID;
  const googleClientSecret =
    readFileIfExistsSync('/opt/creds/google_oauth_client_secret/secret_string') ??
    process.env.GOOGLE_CLIENT_SECRET;

  if (!googleClientId || !googleClientSecret) {
    console.log('🔥 RUH-ROH: missing google oauth secrets');
    // throw new Error('GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables are required');
  }

  // Database configuration
  const databaseUrl =
    readFileIfExistsSync('/opt/creds/postgres_connection_url/secret_string') ??
    process.env.DATABASE_URL;

  if (!databaseUrl) {
    throw new Error('DATABASE_URL environment variable is required');
  }

  return {
    port: parseInt(process.env.PORT || '3002'),
    nodeEnv: process.env.NODE_ENV || 'development',
    localStoragePath: resolve(__dirname, process.env.DATA_ROOT || createTempDir()),
    oauth: {
      google: {
        clientId: googleClientId ?? '<not set>',
        clientSecret: googleClientSecret ?? '<not set>',
        redirectUri:
          process.env.GOOGLE_REDIRECT_URI || 'http://localhost:3002/api/auth/google/callback',
      },
    },
    database: {
      url: databaseUrl,
    },
  };
};
