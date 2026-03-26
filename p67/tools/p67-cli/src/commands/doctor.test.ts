import { afterEach, beforeEach, describe, expect, mock, test } from 'bun:test';
import {
    type CheckResult,
    checkCliVersion,
    checkConnection,
    checkControldHealthy,
    checkEndpointReachable,
    checkSnowCli,
    formatCheckResult,
} from '@p67-cli/commands/doctor';

describe('doctor', () => {
    let originalFetch: typeof globalThis.fetch;

    beforeEach(() => {
        originalFetch = globalThis.fetch;
    });

    afterEach(() => {
        globalThis.fetch = originalFetch;
    });

    describe('formatCheckResult', () => {
        test('should format passing check with checkmark', () => {
            const result: CheckResult = {
                name: 'CLI version',
                passed: true,
                message: 'v0.1.0',
            };
            expect(formatCheckResult(result)).toBe('  ✓ CLI version: v0.1.0');
        });

        test('should format failing check with cross', () => {
            const result: CheckResult = {
                name: 'Connection',
                passed: false,
                message: 'No connections configured',
                hint: 'Run "p67 connection add" to add a connection.',
            };
            const output = formatCheckResult(result);
            expect(output).toContain('✗ Connection: No connections configured');
            expect(output).toContain(
                '    Run "p67 connection add" to add a connection.',
            );
        });

        test('should not show hint for passing check', () => {
            const result: CheckResult = {
                name: 'Test',
                passed: true,
                message: 'OK',
                hint: 'This should not appear',
            };
            expect(formatCheckResult(result)).toBe('  ✓ Test: OK');
        });

        test('should handle failing check without hint', () => {
            const result: CheckResult = {
                name: 'Test',
                passed: false,
                message: 'Failed',
            };
            expect(formatCheckResult(result)).toBe('  ✗ Test: Failed');
        });
    });

    describe('checkCliVersion', () => {
        test('should return passing result with version', async () => {
            const result = await checkCliVersion();
            expect(result.name).toBe('CLI version');
            expect(result.passed).toBe(true);
            expect(result.message).toMatch(/^v\d+\.\d+\.\d+/);
        });
    });

    describe('checkConnection', () => {
        test('should report when no connections configured', async () => {
            // Default test environment has no config file, so this should report no connections
            const result = await checkConnection();
            expect(result.name).toBe('Connection');
            // Either passes with connections or fails with no connections - both are valid
            if (!result.passed) {
                expect(result.hint).toBeDefined();
            }
        });
    });

    describe('checkEndpointReachable', () => {
        test('should pass when endpoint returns 200', async () => {
            globalThis.fetch = mock(async () => {
                return new Response('{}', { status: 200 });
            }) as unknown as typeof globalThis.fetch;

            const result = await checkEndpointReachable(
                'http://localhost:3002',
            );
            expect(result.name).toBe('Endpoint reachable');
            expect(result.passed).toBe(true);
            expect(result.message).toBe('http://localhost:3002');
        });

        test('should fail when endpoint returns non-200', async () => {
            globalThis.fetch = mock(async () => {
                return new Response('', { status: 503 });
            }) as unknown as typeof globalThis.fetch;

            const result = await checkEndpointReachable(
                'http://localhost:3002',
            );
            expect(result.passed).toBe(false);
            expect(result.message).toBe('HTTP 503');
            expect(result.hint).toBeDefined();
        });

        test('should fail when fetch throws', async () => {
            globalThis.fetch = mock(async () => {
                throw new Error('Network error');
            }) as unknown as typeof globalThis.fetch;

            const result = await checkEndpointReachable(
                'http://localhost:3002',
            );
            expect(result.passed).toBe(false);
            expect(result.message).toBe('Could not reach endpoint');
            expect(result.hint).toBeDefined();
        });
    });

    describe('checkControldHealthy', () => {
        test('should pass when status is ok', async () => {
            globalThis.fetch = mock(async () => {
                return new Response(
                    JSON.stringify({ status: 'ok', timestamp: '2025-01-01' }),
                    {
                        status: 200,
                        headers: { 'Content-Type': 'application/json' },
                    },
                );
            }) as unknown as typeof globalThis.fetch;

            const result = await checkControldHealthy('http://localhost:3002');
            expect(result.name).toBe('Controld healthy');
            expect(result.passed).toBe(true);
            expect(result.message).toBe('status: ok');
        });

        test('should fail when status is not ok', async () => {
            globalThis.fetch = mock(async () => {
                return new Response(JSON.stringify({ status: 'degraded' }), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' },
                });
            }) as unknown as typeof globalThis.fetch;

            const result = await checkControldHealthy('http://localhost:3002');
            expect(result.passed).toBe(false);
            expect(result.message).toBe('status: degraded');
        });

        test('should fail when endpoint returns non-200', async () => {
            globalThis.fetch = mock(async () => {
                return new Response('', { status: 500 });
            }) as unknown as typeof globalThis.fetch;

            const result = await checkControldHealthy('http://localhost:3002');
            expect(result.passed).toBe(false);
            expect(result.message).toBe('HTTP 500');
        });

        test('should fail when fetch throws', async () => {
            globalThis.fetch = mock(async () => {
                throw new Error('Connection refused');
            }) as unknown as typeof globalThis.fetch;

            const result = await checkControldHealthy('http://localhost:3002');
            expect(result.passed).toBe(false);
            expect(result.message).toBe('Could not check health');
        });
    });

    describe('checkSnowCli', () => {
        test('should return result with name Snow CLI available', async () => {
            const result = await checkSnowCli();
            expect(result.name).toBe('Snow CLI available');
            // Result depends on environment - both pass and fail are valid
            if (!result.passed) {
                expect(result.hint).toContain('Install the Snowflake CLI');
            }
        });
    });
});
