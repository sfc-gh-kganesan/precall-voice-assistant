import { describe, expect, it } from 'vitest';

/**
 * Tests for the host-side env var resolution logic.
 *
 * The actual code lives in host.ts inside handleMessage(), but we test
 * the resolution logic in isolation by replicating the algorithm against
 * a config Map + secretEnvMappings, with mocked process.env values.
 */

type P67ConfigValue = Record<string, unknown>;

/**
 * Replicates the resolution logic from host.ts:228-261.
 * Given a deserialized config and secretEnvMappings, resolves env vars
 * into the config map.
 */
function resolveSecretEnvMappings(
    config: Map<string, P67ConfigValue>,
    secretEnvMappings: Record<string, string>,
    env: Record<string, string>,
): void {
    for (const [fieldPath, envVarName] of Object.entries(secretEnvMappings)) {
        const value = env[envVarName];
        if (!value) continue;

        const parts = fieldPath.split('.');
        if (parts[0] === 'config' && parts.length >= 3) {
            const configName = parts[1];
            const configEntry = config.get(configName);
            if (configEntry && typeof configEntry === 'object') {
                if (parts.length === 3) {
                    configEntry[parts[2]] = value;
                } else if (parts.length === 4 && parts[2] === 'parameters') {
                    if (!configEntry.parameters) {
                        configEntry.parameters = {};
                    }
                    (configEntry.parameters as Record<string, string>)[
                        parts[3]
                    ] = value;
                }
            }
        }
    }
}

describe('host secret env var resolution', () => {
    it('should resolve a direct config field (config.snowflake.token)', () => {
        const config = new Map<string, P67ConfigValue>([
            [
                'snowflake',
                {
                    account: 'MY_ACCOUNT',
                    token: '__SPCS_SECRET_PENDING__',
                },
            ],
        ]);

        resolveSecretEnvMappings(
            config,
            { 'config.snowflake.token': 'P67_SECRET_0' },
            { P67_SECRET_0: 'my-real-token' },
        );

        expect(config.get('snowflake')?.token).toBe('my-real-token');
        expect(config.get('snowflake')?.account).toBe('MY_ACCOUNT');
    });

    it('should resolve a nested parameters field (config.snowflake.parameters.API_KEY)', () => {
        const config = new Map<string, P67ConfigValue>([
            [
                'snowflake',
                {
                    account: 'MY_ACCOUNT',
                    parameters: {
                        API_KEY: '__SPCS_SECRET_PENDING__',
                        OTHER: 'unchanged',
                    },
                },
            ],
        ]);

        resolveSecretEnvMappings(
            config,
            { 'config.snowflake.parameters.API_KEY': 'P67_SECRET_0' },
            { P67_SECRET_0: 'sk-real-key' },
        );

        const params = config.get('snowflake')?.parameters as Record<
            string,
            string
        >;
        expect(params.API_KEY).toBe('sk-real-key');
        expect(params.OTHER).toBe('unchanged');
    });

    it('should create parameters object if it does not exist', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { account: 'MY_ACCOUNT' }],
        ]);

        resolveSecretEnvMappings(
            config,
            { 'config.snowflake.parameters.NEW_KEY': 'P67_SECRET_0' },
            { P67_SECRET_0: 'new-value' },
        );

        const params = config.get('snowflake')?.parameters as Record<
            string,
            string
        >;
        expect(params.NEW_KEY).toBe('new-value');
    });

    it('should resolve multiple secrets', () => {
        const config = new Map<string, P67ConfigValue>([
            [
                'snowflake',
                {
                    token: '__SPCS_SECRET_PENDING__',
                    password: '__SPCS_SECRET_PENDING__',
                },
            ],
        ]);

        resolveSecretEnvMappings(
            config,
            {
                'config.snowflake.token': 'P67_SECRET_0',
                'config.snowflake.password': 'P67_SECRET_1',
            },
            {
                P67_SECRET_0: 'token-value',
                P67_SECRET_1: 'password-value',
            },
        );

        expect(config.get('snowflake')?.token).toBe('token-value');
        expect(config.get('snowflake')?.password).toBe('password-value');
    });

    it('should skip resolution when env var is not set', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { token: '__SPCS_SECRET_PENDING__' }],
        ]);

        resolveSecretEnvMappings(
            config,
            { 'config.snowflake.token': 'P67_SECRET_0' },
            {}, // env var not set
        );

        expect(config.get('snowflake')?.token).toBe('__SPCS_SECRET_PENDING__');
    });

    it('should skip resolution when config entry does not exist', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { account: 'MY_ACCOUNT' }],
        ]);

        // References a config entry "other" that doesn't exist
        resolveSecretEnvMappings(
            config,
            { 'config.other.token': 'P67_SECRET_0' },
            { P67_SECRET_0: 'some-value' },
        );

        // No crash, config unchanged
        expect(config.get('snowflake')?.account).toBe('MY_ACCOUNT');
        expect(config.get('other')).toBeUndefined();
    });

    it('should ignore paths that are not config.*', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { token: 'original' }],
        ]);

        resolveSecretEnvMappings(
            config,
            { 'other.snowflake.token': 'P67_SECRET_0' },
            { P67_SECRET_0: 'injected' },
        );

        expect(config.get('snowflake')?.token).toBe('original');
    });

    it('should ignore paths with only 2 parts', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { token: 'original' }],
        ]);

        resolveSecretEnvMappings(
            config,
            { 'config.snowflake': 'P67_SECRET_0' },
            { P67_SECRET_0: 'injected' },
        );

        expect(config.get('snowflake')?.token).toBe('original');
    });

    it('should handle mix of direct fields and parameters', () => {
        const config = new Map<string, P67ConfigValue>([
            [
                'snowflake',
                {
                    token: '__SPCS_SECRET_PENDING__',
                    parameters: {
                        API_KEY: '__SPCS_SECRET_PENDING__',
                    },
                },
            ],
        ]);

        resolveSecretEnvMappings(
            config,
            {
                'config.snowflake.token': 'P67_SECRET_0',
                'config.snowflake.parameters.API_KEY': 'P67_SECRET_1',
            },
            {
                P67_SECRET_0: 'real-token',
                P67_SECRET_1: 'real-api-key',
            },
        );

        expect(config.get('snowflake')?.token).toBe('real-token');
        const params = config.get('snowflake')?.parameters as Record<
            string,
            string
        >;
        expect(params.API_KEY).toBe('real-api-key');
    });

    it('should not resolve empty secretEnvMappings', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { token: 'original' }],
        ]);

        resolveSecretEnvMappings(config, {}, { P67_SECRET_0: 'injected' });

        expect(config.get('snowflake')?.token).toBe('original');
    });
});
