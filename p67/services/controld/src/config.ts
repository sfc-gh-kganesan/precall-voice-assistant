import { readFileSync, existsSync, mkdtempSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { tmpdir } from 'os';
import { fileURLToPath } from 'url';
import { config as dotenvConfig } from 'dotenv';

if (process.env.NODE_ENV != 'prod') {
  dotenvConfig();
}

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
  debug: {
    enableDefaultUser: boolean;
    defaultUser?: string;
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
    // throw new Error('DATABASE_URL environment variable is required');
    console.log('🔥 RUH-ROH: missing database url');
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
      url: databaseUrl ?? '',
    },
    debug: {
      enableDefaultUser: process.env.DEBUG_ENABLE_DEFAULT_USER == 'true',
      defaultUser: process.env.DEBUG_DEFAULT_USER,
    },
  };
};
