import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { config as dotenvConfig } from 'dotenv';

if (process.env.NODE_ENV !== 'prod') {
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

export type SandboxConfig =
    | {
          mode: 'docker';
          runnerImage: string;
          hostStorageRoot?: string;
          containerStorageRoot?: string;
      }
    | {
          mode: 'spcs';
          runnerImage: string;
          computePool: string;
          warehouseName: string;
          stageName: string;
      };

export type ServerConfig = {
    port: number;
    nodeEnv: string;
    localStoragePath: string;
    oauth: OAuthConfig;
    database: {
        url: string;
    };
    encryption: {
        key: string;
    };
    debug: {
        enableDefaultUser: boolean;
        defaultUser?: string;
    };
    sandbox: SandboxConfig;
};

function readFileIfExistsSync(filePath: string): string | null {
    if (!existsSync(filePath)) {
        return null;
    }

    return readFileSync(filePath, 'utf-8');
}

function buildSandboxConfig(localStoragePath: string): SandboxConfig {
    const runnerImage = process.env.P67_RUNNER_IMAGE || 'p67-runner:latest';

    // SPCS mode is detected by the presence of SNOWFLAKE_HOST (injected by SPCS runtime)
    // or explicitly via P67_SANDBOX_MODE=spcs
    const isSpcs =
        process.env.P67_SANDBOX_MODE === 'spcs' || !!process.env.SNOWFLAKE_HOST;

    if (isSpcs) {
        return {
            mode: 'spcs',
            runnerImage,
            computePool:
                process.env.P67_RUNNER_COMPUTE_POOL || 'runner_compute_pool',
            warehouseName: process.env.P67_RUNNER_WAREHOUSE || 'p67_app_wh',
            stageName: process.env.P67_WORKFLOW_STAGE || 'app.workflow_stage',
        };
    }

    return {
        mode: 'docker',
        runnerImage,
        hostStorageRoot: process.env.P67_HOST_STORAGE_ROOT || undefined,
        containerStorageRoot: localStoragePath,
    };
}

export const loadConfig = (): ServerConfig => {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);

    // Validate required OAuth env vars
    const googleClientId =
        readFileIfExistsSync(
            '/opt/creds/google_oauth_client_id/secret_string',
        ) ?? process.env.GOOGLE_CLIENT_ID;
    const googleClientSecret =
        readFileIfExistsSync(
            '/opt/creds/google_oauth_client_secret/secret_string',
        ) ?? process.env.GOOGLE_CLIENT_SECRET;

    if (!googleClientId || !googleClientSecret) {
        console.log('🔥 RUH-ROH: missing google oauth secrets');
        // throw new Error('GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables are required');
    }

    // Database configuration
    const databaseUrl =
        readFileIfExistsSync(
            '/opt/creds/postgres_connection_url/secret_string',
        ) ?? process.env.DATABASE_URL;

    if (!databaseUrl) {
        // throw new Error('DATABASE_URL environment variable is required');
        console.log('🔥 RUH-ROH: missing database url');
    }

    // Encryption key for secrets
    const encryptionKey =
        readFileIfExistsSync('/opt/creds/encryption_key/secret_string') ??
        process.env.ENCRYPTION_KEY;

    if (!encryptionKey) {
        console.log('🔥 RUH-ROH: missing encryption key');
    }

    const localStoragePath = resolve(
        __dirname,
        process.env.DATA_ROOT || createTempDir(),
    );

    return {
        port: parseInt(process.env.PORT || '3002', 10),
        nodeEnv: process.env.NODE_ENV || 'development',
        localStoragePath,
        oauth: {
            google: {
                clientId: googleClientId ?? '<not set>',
                clientSecret: googleClientSecret ?? '<not set>',
                redirectUri:
                    process.env.GOOGLE_REDIRECT_URI ||
                    'http://localhost:3002/api/auth/google/callback',
            },
        },
        database: {
            url: databaseUrl ?? '',
        },
        encryption: {
            key: encryptionKey ?? '',
        },
        debug: {
            enableDefaultUser: process.env.DEBUG_ENABLE_DEFAULT_USER === 'true',
            defaultUser: process.env.DEBUG_DEFAULT_USER,
        },
        sandbox: buildSandboxConfig(localStoragePath),
    };
};
