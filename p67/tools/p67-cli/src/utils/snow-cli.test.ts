import { beforeEach, describe, expect, mock, test } from 'bun:test';
import {
    discoverEndpoint,
    isSnowInstalled,
    parseEndpointFromOutput,
} from '@p67-cli/utils/snow-cli';

describe('parseEndpointFromOutput', () => {
    test('should parse a valid endpoint URL from snow sql JSON output', () => {
        const output = JSON.stringify([
            { 'P67.V1.APP_URL()': 'https://example.snowflakecomputing.app' },
        ]);
        expect(parseEndpointFromOutput(output)).toBe(
            'https://example.snowflakecomputing.app',
        );
    });

    test('should parse URL regardless of column name', () => {
        const output = JSON.stringify([
            { APP_URL: 'https://my-app.snowflakecomputing.app' },
        ]);
        expect(parseEndpointFromOutput(output)).toBe(
            'https://my-app.snowflakecomputing.app',
        );
    });

    test('should trim whitespace from the URL', () => {
        const output = JSON.stringify([
            {
                'P67.V1.APP_URL()':
                    '  https://example.snowflakecomputing.app  ',
            },
        ]);
        expect(parseEndpointFromOutput(output)).toBe(
            'https://example.snowflakecomputing.app',
        );
    });

    test('should throw on invalid JSON', () => {
        expect(() => parseEndpointFromOutput('not json')).toThrow(
            'Failed to parse snow sql output as JSON',
        );
    });

    test('should throw on empty array', () => {
        expect(() => parseEndpointFromOutput('[]')).toThrow(
            'expected non-empty array',
        );
    });

    test('should throw on non-array JSON', () => {
        expect(() => parseEndpointFromOutput('{"key":"value"}')).toThrow(
            'expected non-empty array',
        );
    });

    test('should throw when row has no columns', () => {
        expect(() => parseEndpointFromOutput('[{}]')).toThrow(
            'No columns in snow sql output row',
        );
    });

    test('should throw when value is not a string', () => {
        expect(() => parseEndpointFromOutput('[{"col": 123}]')).toThrow(
            'Expected a URL string',
        );
    });

    test('should throw when value is an empty string', () => {
        expect(() => parseEndpointFromOutput('[{"col": ""}]')).toThrow(
            'Expected a URL string',
        );
    });

    test('should throw when value is not a valid URL', () => {
        expect(() => parseEndpointFromOutput('[{"col": "://bad"}]')).toThrow(
            'not a valid URL',
        );
    });

    test('should prepend https:// to bare hostname', () => {
        const output = JSON.stringify([
            {
                'P67.V1.APP_URL()':
                    'abc123-sfengineering-aifde.snowflakecomputing.app',
            },
        ]);
        expect(parseEndpointFromOutput(output)).toBe(
            'https://abc123-sfengineering-aifde.snowflakecomputing.app',
        );
    });

    test('should not double-prefix URLs that already have https://', () => {
        const output = JSON.stringify([
            { 'P67.V1.APP_URL()': 'https://example.snowflakecomputing.app' },
        ]);
        expect(parseEndpointFromOutput(output)).toBe(
            'https://example.snowflakecomputing.app',
        );
    });
});

describe('isSnowInstalled', () => {
    let originalSpawnSync: typeof Bun.spawnSync;

    beforeEach(() => {
        originalSpawnSync = Bun.spawnSync;
    });

    test('should return true when snow --version succeeds', () => {
        Bun.spawnSync = mock(() => ({
            exitCode: 0,
            stdout: Buffer.from('snow 1.0.0'),
            stderr: Buffer.from(''),
        })) as never;

        expect(isSnowInstalled()).toBe(true);

        Bun.spawnSync = originalSpawnSync;
    });

    test('should return false when snow --version fails', () => {
        Bun.spawnSync = mock(() => ({
            exitCode: 1,
            stdout: Buffer.from(''),
            stderr: Buffer.from('not found'),
        })) as never;

        expect(isSnowInstalled()).toBe(false);

        Bun.spawnSync = originalSpawnSync;
    });

    test('should return false when spawn throws', () => {
        Bun.spawnSync = mock(() => {
            throw new Error('ENOENT');
        }) as never;

        expect(isSnowInstalled()).toBe(false);

        Bun.spawnSync = originalSpawnSync;
    });
});

describe('discoverEndpoint', () => {
    let originalSpawnSync: typeof Bun.spawnSync;
    let originalSpawn: typeof Bun.spawn;

    beforeEach(() => {
        originalSpawnSync = Bun.spawnSync;
        originalSpawn = Bun.spawn;
    });

    function mockSnowInstalled() {
        Bun.spawnSync = mock(() => ({
            exitCode: 0,
            stdout: Buffer.from('snow 1.0.0'),
            stderr: Buffer.from(''),
        })) as never;
    }

    function mockSnowNotInstalled() {
        Bun.spawnSync = mock(() => ({
            exitCode: 1,
            stdout: Buffer.from(''),
            stderr: Buffer.from(''),
        })) as never;
    }

    function mockSpawnSuccess(stdout: string) {
        Bun.spawn = mock(() => ({
            exited: Promise.resolve(0),
            stdout: new ReadableStream({
                start(controller) {
                    controller.enqueue(new TextEncoder().encode(stdout));
                    controller.close();
                },
            }),
            stderr: new ReadableStream({
                start(controller) {
                    controller.close();
                },
            }),
        })) as never;
    }

    function mockSpawnFailure(stderr: string) {
        Bun.spawn = mock(() => ({
            exited: Promise.resolve(1),
            stdout: new ReadableStream({
                start(controller) {
                    controller.close();
                },
            }),
            stderr: new ReadableStream({
                start(controller) {
                    controller.enqueue(new TextEncoder().encode(stderr));
                    controller.close();
                },
            }),
        })) as never;
    }

    function restore() {
        Bun.spawnSync = originalSpawnSync;
        Bun.spawn = originalSpawn;
    }

    test('should throw when snow is not installed', async () => {
        mockSnowNotInstalled();

        await expect(discoverEndpoint()).rejects.toThrow(
            '`snow` CLI is not installed',
        );

        restore();
    });

    test('should return discovered endpoint URL', async () => {
        mockSnowInstalled();
        const jsonOutput = JSON.stringify([
            {
                'P67.V1.APP_URL()': 'https://abc123.snowflakecomputing.app',
            },
        ]);
        mockSpawnSuccess(jsonOutput);

        const result = await discoverEndpoint();
        expect(result).toBe('https://abc123.snowflakecomputing.app');

        restore();
    });

    test('should pass snow connection name via -c flag', async () => {
        mockSnowInstalled();
        const jsonOutput = JSON.stringify([
            {
                'P67.V1.APP_URL()': 'https://abc123.snowflakecomputing.app',
            },
        ]);
        mockSpawnSuccess(jsonOutput);

        await discoverEndpoint('my-connection');

        const spawnMock = Bun.spawn as ReturnType<typeof mock>;
        const callArgs = spawnMock.mock.calls[0]?.[0] as string[];
        expect(callArgs).toContain('-c');
        expect(callArgs).toContain('my-connection');

        restore();
    });

    test('should throw when snow sql returns non-zero exit code', async () => {
        mockSnowInstalled();
        mockSpawnFailure('SQL compilation error');

        await expect(discoverEndpoint()).rejects.toThrow(
            'snow sql failed: SQL compilation error',
        );

        restore();
    });
});
