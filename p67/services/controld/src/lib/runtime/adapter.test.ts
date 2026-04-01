import * as fs from 'node:fs';
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

describe('SPCSAdapter.buildStageUploadSQL', () => {
    const tmpBase = `/tmp/p67-adapter-test-${Date.now()}`;

    function setupDir(files: string[], dirs: string[]): string {
        const dir = `${tmpBase}/${Math.random().toString(36).slice(2)}`;
        fs.mkdirSync(dir, { recursive: true });
        for (const f of files) {
            fs.writeFileSync(`${dir}/${f}`, 'test');
        }
        for (const d of dirs) {
            fs.mkdirSync(`${dir}/${d}`, { recursive: true });
            fs.writeFileSync(`${dir}/${d}/file.txt`, 'test');
        }
        return dir;
    }

    it('should use single glob when no subdirectories exist', () => {
        const dir = setupDir(['index.js', 'manifest.yaml'], []);
        const adapter = createAdapter();
        const { putStatements, stagePath } = adapter.buildStageUploadSQL(
            'runner_test',
            dir,
        );

        expect(stagePath).toBe('runner_test');
        expect(putStatements).toHaveLength(1);
        expect(putStatements[0]).toContain(`PUT 'file://${dir}/*'`);
        expect(putStatements[0]).toContain('@test_stage/runner_test/');
    });

    it('should upload files individually and subdirs with glob when subdirectories exist', () => {
        const dir = setupDir(['index.js', 'manifest.yaml'], ['p67_sdk']);
        const adapter = createAdapter();
        const { putStatements } = adapter.buildStageUploadSQL(
            'runner_test',
            dir,
        );

        // 2 individual files + 1 subdir glob = 3 statements
        expect(putStatements).toHaveLength(3);

        // Top-level files uploaded individually (no wildcard glob)
        expect(putStatements[0]).toContain(`PUT 'file://${dir}/index.js'`);
        expect(putStatements[1]).toContain(`PUT 'file://${dir}/manifest.yaml'`);

        // Subdirectory uploaded with its own glob
        expect(putStatements[2]).toContain(`PUT 'file://${dir}/p67_sdk/*'`);
        expect(putStatements[2]).toContain('@test_stage/runner_test/p67_sdk/');
    });

    it('should handle multiple subdirectories', () => {
        const dir = setupDir(['main.py'], ['p67_sdk', 'utils']);
        const adapter = createAdapter();
        const { putStatements } = adapter.buildStageUploadSQL(
            'runner_test',
            dir,
        );

        // 1 file + 2 subdir globs = 3 statements
        expect(putStatements).toHaveLength(3);
        expect(putStatements[0]).toContain(`PUT 'file://${dir}/main.py'`);
        expect(putStatements[1]).toContain(`PUT 'file://${dir}/p67_sdk/*'`);
        expect(putStatements[1]).toContain('@test_stage/runner_test/p67_sdk/');
        expect(putStatements[2]).toContain(`PUT 'file://${dir}/utils/*'`);
        expect(putStatements[2]).toContain('@test_stage/runner_test/utils/');
    });

    it('should never use top-level glob when subdirectories are present', () => {
        const dir = setupDir(['main.py'], ['p67_sdk']);
        const adapter = createAdapter();
        const { putStatements } = adapter.buildStageUploadSQL(
            'runner_test',
            dir,
        );

        // No statement should be a top-level dir/* glob (which causes EISDIR)
        for (const stmt of putStatements) {
            expect(stmt).not.toMatch(
                new RegExp(
                    `PUT 'file://${dir.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/\\*'`,
                ),
            );
        }
    });

    it('should include AUTO_COMPRESS and OVERWRITE in all statements', () => {
        const dir = setupDir(['index.js'], ['p67_sdk']);
        const adapter = createAdapter();
        const { putStatements } = adapter.buildStageUploadSQL(
            'runner_test',
            dir,
        );

        for (const stmt of putStatements) {
            expect(stmt).toContain('AUTO_COMPRESS=FALSE');
            expect(stmt).toContain('OVERWRITE=TRUE');
        }
    });
});
