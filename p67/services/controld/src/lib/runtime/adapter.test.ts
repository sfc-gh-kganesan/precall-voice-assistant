import { SPCSAdapter } from '@controld/lib/runtime/adapter.js';
import { describe, expect, it } from 'vitest';
import { makeRunWorkflowMessage } from './schema.js';

const testConfig = {
    snowflakeConfig: {},
    parameters: {},
};

function createAdapter(): SPCSAdapter {
    return new SPCSAdapter('typescript', {
        mode: 'spcs' as const,
        runnerImage: 'test-image:latest',
        computePool: 'test_pool',
        warehouseName: 'test_wh',
        stageName: 'test_stage',
    });
}

const testMessage = makeRunWorkflowMessage({
    dir: '/workflow',
    config: testConfig,
});

describe('SPCSAdapter.buildJobServiceSQL - secrets', () => {
    it('should generate spec without secrets block when no secrets provided', () => {
        const adapter = createAdapter();
        const sql = adapter.buildJobServiceSQL(
            'runner_test',
            'stage/path',
            testMessage,
        );

        expect(sql).toContain('EXECUTE JOB SERVICE');
        expect(sql).not.toContain('secrets:');
        expect(sql).not.toContain('snowflakeSecret:');
    });

    it('should generate spec without secrets block when empty array provided', () => {
        const adapter = createAdapter();
        const sql = adapter.buildJobServiceSQL(
            'runner_test',
            'stage/path',
            testMessage,
            undefined,
            undefined,
            [],
        );

        expect(sql).not.toContain('secrets:');
    });

    it('should include secrets block when secrets are provided', () => {
        const adapter = createAdapter();
        const secrets = [
            {
                objectName: 'mydb.myschema.my_token',
                envVarName: 'P67_SECRET_0',
            },
        ];

        const sql = adapter.buildJobServiceSQL(
            'runner_test',
            'stage/path',
            testMessage,
            undefined,
            undefined,
            secrets,
        );

        expect(sql).toContain('secrets:');
        expect(sql).toContain('snowflakeSecret:');
        expect(sql).toContain('objectName: mydb.myschema.my_token');
        expect(sql).toContain('secretKeyRef: secret_string');
        expect(sql).toContain('envVarName: P67_SECRET_0');
    });

    it('should include multiple secrets in the block', () => {
        const adapter = createAdapter();
        const secrets = [
            {
                objectName: 'db.schema.secret_one',
                envVarName: 'P67_SECRET_0',
            },
            {
                objectName: 'db.schema.secret_two',
                envVarName: 'P67_SECRET_1',
            },
        ];

        const sql = adapter.buildJobServiceSQL(
            'runner_test',
            'stage/path',
            testMessage,
            undefined,
            undefined,
            secrets,
        );

        expect(sql).toContain('objectName: db.schema.secret_one');
        expect(sql).toContain('envVarName: P67_SECRET_0');
        expect(sql).toContain('objectName: db.schema.secret_two');
        expect(sql).toContain('envVarName: P67_SECRET_1');
    });

    it('should still include other spec elements alongside secrets', () => {
        const adapter = createAdapter();
        const secrets = [
            {
                objectName: 'db.schema.my_secret',
                envVarName: 'P67_SECRET_0',
            },
        ];

        const sql = adapter.buildJobServiceSQL(
            'runner_test',
            'stage/path',
            testMessage,
            undefined,
            'http://controld.test:80',
            secrets,
        );

        // Core spec elements still present
        expect(sql).toContain('EXECUTE JOB SERVICE');
        expect(sql).toContain('IN COMPUTE POOL test_pool');
        expect(sql).toContain('QUERY_WAREHOUSE = test_wh');
        expect(sql).toContain('image: test-image:latest');
        expect(sql).toContain('P67_RUN_MESSAGE_B64');
        expect(sql).toContain('P67_CONTROLD_URL: "http://controld.test:80"');
        expect(sql).toContain('workflow-files');
        expect(sql).toContain('results');
        // And secrets
        expect(sql).toContain('objectName: db.schema.my_secret');
    });
});
