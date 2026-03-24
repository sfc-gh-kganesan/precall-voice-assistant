import type { Manifest } from '@controld/lib/manifest.js';
import { collectSnowflakeSecrets } from '@controld/lib/runner.js';
import { describe, expect, it } from 'vitest';

/**
 * Tests for serializeConfig behavior with secretEnvMappings,
 * and for placeholder replacement of FQN secretRefs before hydration.
 *
 * These test the logic that Runner uses, replicated here since
 * serializeConfig is private and Runner requires PrismaClient to construct.
 */

type P67ConfigValue = Record<string, unknown>;
type SerializedP67Config = {
    snowflakeConfig: Record<string, P67ConfigValue>;
    parameters: Record<string, string>;
    secretEnvMappings?: Record<string, string>;
};

/**
 * Replicates Runner.serializeConfig() logic.
 */
function serializeConfig(
    snowflakeConfig: Map<string, P67ConfigValue>,
    mergedParams: Record<string, string>,
    collectedSecrets: ReturnType<typeof collectSnowflakeSecrets> | null,
): SerializedP67Config {
    const serialized: SerializedP67Config = {
        snowflakeConfig: Object.fromEntries(snowflakeConfig),
        parameters: mergedParams,
    };

    if (collectedSecrets?.specSecrets.length) {
        serialized.secretEnvMappings = collectedSecrets.envMappings;
    }

    return serialized;
}

describe('serializeConfig with secretEnvMappings', () => {
    it('should not include secretEnvMappings when collectedSecrets is null', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { account: 'MY_ACCOUNT' }],
        ]);

        const result = serializeConfig(config, {}, null);

        expect(result.secretEnvMappings).toBeUndefined();
        expect(result.snowflakeConfig.snowflake.account).toBe('MY_ACCOUNT');
    });

    it('should not include secretEnvMappings when specSecrets is empty', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { account: 'MY_ACCOUNT' }],
        ]);

        const collected = { specSecrets: [], envMappings: {} };
        const result = serializeConfig(config, {}, collected);

        expect(result.secretEnvMappings).toBeUndefined();
    });

    it('should include secretEnvMappings when secrets are collected', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { account: 'MY_ACCOUNT', token: 'placeholder' }],
        ]);

        const collected = {
            specSecrets: [
                { objectName: 'db.schema.token', envVarName: 'P67_SECRET_0' },
            ],
            envMappings: { 'config.snowflake.token': 'P67_SECRET_0' },
        };

        const result = serializeConfig(config, { THRESHOLD: '0.5' }, collected);

        expect(result.secretEnvMappings).toEqual({
            'config.snowflake.token': 'P67_SECRET_0',
        });
        expect(result.parameters).toEqual({ THRESHOLD: '0.5' });
    });

    it('should include multiple env mappings', () => {
        const config = new Map<string, P67ConfigValue>([
            ['snowflake', { token: 'p1', password: 'p2' }],
        ]);

        const collected = {
            specSecrets: [
                { objectName: 'db.schema.tok', envVarName: 'P67_SECRET_0' },
                { objectName: 'db.schema.pw', envVarName: 'P67_SECRET_1' },
            ],
            envMappings: {
                'config.snowflake.token': 'P67_SECRET_0',
                'config.snowflake.password': 'P67_SECRET_1',
            },
        };

        const result = serializeConfig(config, {}, collected);

        expect(result.secretEnvMappings).toEqual({
            'config.snowflake.token': 'P67_SECRET_0',
            'config.snowflake.password': 'P67_SECRET_1',
        });
    });
});

/**
 * Replicates the placeholder replacement logic from Runner.start().
 * Given a manifest and collected secrets, replaces FQN secretRefs with
 * placeholder values so ValueManager (Postgres) doesn't try to resolve them.
 */
function applyPlaceholders(manifest: Manifest, collectedFQNs: Set<string>) {
    const configFields = [
        'account',
        'username',
        'authenticator',
        'accessUrl',
        'token',
        'password',
        'warehouse',
        'database',
        'schema',
        'email_integration',
    ] as const;

    for (const configEntry of manifest.config) {
        for (const field of configFields) {
            const val = configEntry[field];
            if (val?.secretRef && collectedFQNs.has(val.secretRef)) {
                val.value = '__SPCS_SECRET_PENDING__';
                val.secretRef = undefined;
            }
        }
        if (configEntry.parameters) {
            for (const val of Object.values(configEntry.parameters)) {
                if (val?.secretRef && collectedFQNs.has(val.secretRef)) {
                    val.value = '__SPCS_SECRET_PENDING__';
                    val.secretRef = undefined;
                }
            }
        }
    }
}

function makeManifest(overrides: Partial<Manifest> = {}): Manifest {
    return { config: [], ...overrides };
}

describe('placeholder replacement for FQN secretRefs', () => {
    it('should replace FQN secretRef with placeholder', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'db.schema.my_token' },
                },
            ],
        });

        applyPlaceholders(manifest, new Set(['db.schema.my_token']));

        expect(manifest.config[0].token?.value).toBe('__SPCS_SECRET_PENDING__');
        expect(manifest.config[0].token?.secretRef).toBeUndefined();
    });

    it('should not replace non-FQN secretRef', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'simple_key' },
                },
            ],
        });

        // simple_key is not in the collected FQNs set
        applyPlaceholders(manifest, new Set(['db.schema.other']));

        expect(manifest.config[0].token?.secretRef).toBe('simple_key');
        expect(manifest.config[0].token?.value).toBeUndefined();
    });

    it('should not replace inline values', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    account: { value: 'MY_ACCOUNT' },
                },
            ],
        });

        applyPlaceholders(manifest, new Set(['db.schema.something']));

        expect(manifest.config[0].account?.value).toBe('MY_ACCOUNT');
    });

    it('should replace FQN secretRef in config parameters', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    parameters: {
                        API_KEY: { secretRef: 'db.schema.api_key' },
                        PLAIN: { value: 'hello' },
                    },
                },
            ],
        });

        applyPlaceholders(manifest, new Set(['db.schema.api_key']));

        expect(manifest.config[0].parameters?.API_KEY?.value).toBe(
            '__SPCS_SECRET_PENDING__',
        );
        expect(
            manifest.config[0].parameters?.API_KEY?.secretRef,
        ).toBeUndefined();
        expect(manifest.config[0].parameters?.PLAIN?.value).toBe('hello');
    });

    it('should handle mix of FQN and non-FQN in same config', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'db.schema.sf_token' },
                    password: { secretRef: 'my_pg_password' },
                },
            ],
        });

        applyPlaceholders(manifest, new Set(['db.schema.sf_token']));

        // FQN replaced
        expect(manifest.config[0].token?.value).toBe('__SPCS_SECRET_PENDING__');
        expect(manifest.config[0].token?.secretRef).toBeUndefined();
        // Non-FQN left alone
        expect(manifest.config[0].password?.secretRef).toBe('my_pg_password');
        expect(manifest.config[0].password?.value).toBeUndefined();
    });

    it('should work end-to-end with collectSnowflakeSecrets', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'db.schema.my_token' },
                    account: { value: 'MY_ACCOUNT' },
                    password: { secretRef: 'legacy_pg_key' },
                },
            ],
        });

        const collected = collectSnowflakeSecrets(manifest);
        const collectedFQNs = new Set(
            collected.specSecrets.map((s) => s.objectName),
        );
        applyPlaceholders(manifest, collectedFQNs);

        // FQN token → placeholder
        expect(manifest.config[0].token?.value).toBe('__SPCS_SECRET_PENDING__');
        expect(manifest.config[0].token?.secretRef).toBeUndefined();
        // Inline value → unchanged
        expect(manifest.config[0].account?.value).toBe('MY_ACCOUNT');
        // Non-FQN → unchanged (will go through Postgres)
        expect(manifest.config[0].password?.secretRef).toBe('legacy_pg_key');

        // Collected should have 1 secret
        expect(collected.specSecrets).toHaveLength(1);
        expect(collected.envMappings).toEqual({
            'config.snowflake.token': 'P67_SECRET_0',
        });
    });
});
