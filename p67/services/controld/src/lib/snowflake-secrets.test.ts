import type { Manifest } from '@controld/lib/manifest.js';
import { collectSnowflakeSecrets } from '@controld/lib/runner.js';
import { describe, expect, it } from 'vitest';

/**
 * Builds a minimal valid Manifest for testing.
 * Only the fields relevant to secret collection are populated.
 */
function makeManifest(overrides: Partial<Manifest> = {}): Manifest {
    return {
        config: [],
        ...overrides,
    };
}

describe('collectSnowflakeSecrets', () => {
    it('should collect FQN secretRef values from config entries', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'mydb.myschema.my_token' },
                    account: { value: 'my_account' },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(1);
        expect(result.specSecrets[0]).toEqual({
            objectName: 'mydb.myschema.my_token',
            envVarName: 'P67_SECRET_0',
        });
        expect(result.envMappings).toEqual({
            'config.snowflake.token': 'P67_SECRET_0',
        });
    });

    it('should skip non-FQN secretRef values (simple names)', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'my_simple_key' },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(0);
        expect(result.envMappings).toEqual({});
    });

    it('should skip oauthRef values', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { oauthRef: 'mydb.myschema.my_oauth' },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(0);
    });

    it('should skip inline value fields', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    account: { value: 'my_account' },
                    database: { value: 'my_db' },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(0);
    });

    it('should collect multiple secrets across config fields', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'db.schema.token_secret' },
                    password: { secretRef: 'db.schema.password_secret' },
                    account: { value: 'my_account' },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(2);
        expect(result.specSecrets[0].objectName).toBe('db.schema.token_secret');
        expect(result.specSecrets[0].envVarName).toBe('P67_SECRET_0');
        expect(result.specSecrets[1].objectName).toBe(
            'db.schema.password_secret',
        );
        expect(result.specSecrets[1].envVarName).toBe('P67_SECRET_1');
    });

    it('should collect secrets from config entry parameters', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    parameters: {
                        custom_token: {
                            secretRef: 'db.schema.custom_token',
                        },
                    },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(1);
        expect(result.envMappings).toEqual({
            'config.snowflake.parameters.custom_token': 'P67_SECRET_0',
        });
    });

    it('should handle mixed FQN and non-FQN secretRefs', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'db.schema.sf_token' },
                    password: { secretRef: 'simple_password' },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        // Only the FQN one should be collected
        expect(result.specSecrets).toHaveLength(1);
        expect(result.specSecrets[0].objectName).toBe('db.schema.sf_token');
    });

    it('should reject SQL injection attempts in secretRef', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: {
                        secretRef: 'db.schema.name; DROP TABLE secrets',
                    },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(0);
    });

    it('should reject secretRef with quotes', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: "db.schema.name' OR '1'='1" },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(0);
    });

    it('should reject two-part names (missing schema)', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'db.my_secret' },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(0);
    });

    it('should return empty results for empty manifest', () => {
        const manifest = makeManifest({ config: [] });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(0);
        expect(result.envMappings).toEqual({});
    });

    it('should handle manifest with no params', () => {
        const manifest = makeManifest({
            config: [{ config_name: 'snowflake' }],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(0);
        expect(result.envMappings).toEqual({});
    });

    it('should accept identifiers with dollar signs', () => {
        const manifest = makeManifest({
            config: [
                {
                    config_name: 'snowflake',
                    token: { secretRef: 'MY$DB.MY$SCHEMA.MY$SECRET' },
                },
            ],
        });

        const result = collectSnowflakeSecrets(manifest);

        expect(result.specSecrets).toHaveLength(1);
        expect(result.specSecrets[0].objectName).toBe(
            'MY$DB.MY$SCHEMA.MY$SECRET',
        );
    });
});
