import { Command } from '@p67-cli/Command';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';

export interface CheckResult {
    name: string;
    passed: boolean;
    message: string;
    hint?: string;
}

export async function checkCliVersion(): Promise<CheckResult> {
    try {
        const packageJson = await import('../../package.json');
        const version = packageJson.version as string;
        return {
            name: 'CLI version',
            passed: true,
            message: `v${version}`,
        };
    } catch {
        return {
            name: 'CLI version',
            passed: false,
            message: 'Could not read package.json',
            hint: 'Reinstall the CLI or check your installation path.',
        };
    }
}

export async function checkConnection(): Promise<CheckResult> {
    try {
        const config = new ConnectionConfig();
        const connections = config.getConnections();
        const defaultConn = config.getDefault();

        if (connections.length === 0) {
            return {
                name: 'Connection',
                passed: false,
                message: 'No connections configured',
                hint: 'Run "p67 connection add" to add a connection.',
            };
        }

        const defaultLabel = defaultConn ? `, default: ${defaultConn}` : '';
        return {
            name: 'Connection',
            passed: true,
            message: `${connections.length} connection(s)${defaultLabel}`,
        };
    } catch {
        return {
            name: 'Connection',
            passed: false,
            message: 'Could not read connection config',
            hint: 'Run "p67 connection add" to configure a connection.',
        };
    }
}

export async function checkEndpointReachable(
    endpoint: string,
): Promise<CheckResult> {
    try {
        const url = `${endpoint}/api/health`;
        const response = await fetch(url, {
            signal: AbortSignal.timeout(5000),
        });
        if (response.status === 200) {
            return {
                name: 'Endpoint reachable',
                passed: true,
                message: endpoint,
            };
        }
        return {
            name: 'Endpoint reachable',
            passed: false,
            message: `HTTP ${response.status}`,
            hint: `Endpoint returned ${response.status}. Verify the endpoint URL with "p67 connection list".`,
        };
    } catch {
        return {
            name: 'Endpoint reachable',
            passed: false,
            message: 'Could not reach endpoint',
            hint: 'Check your network connection and verify the endpoint URL.',
        };
    }
}

export async function checkControldHealthy(
    endpoint: string,
): Promise<CheckResult> {
    try {
        const url = `${endpoint}/api/health`;
        const response = await fetch(url, {
            signal: AbortSignal.timeout(5000),
        });
        if (response.status !== 200) {
            return {
                name: 'Controld healthy',
                passed: false,
                message: `HTTP ${response.status}`,
                hint: 'The control daemon may be down. Check service logs.',
            };
        }
        const body = (await response.json()) as { status?: string };
        if (body.status === 'ok') {
            return {
                name: 'Controld healthy',
                passed: true,
                message: 'status: ok',
            };
        }
        return {
            name: 'Controld healthy',
            passed: false,
            message: `status: ${body.status ?? 'unknown'}`,
            hint: 'The control daemon reported an unhealthy status.',
        };
    } catch {
        return {
            name: 'Controld healthy',
            passed: false,
            message: 'Could not check health',
            hint: 'Check your network connection and verify the endpoint URL.',
        };
    }
}

export async function checkSnowCli(): Promise<CheckResult> {
    try {
        const result = Bun.spawnSync(['which', 'snow']);
        if (result.exitCode === 0) {
            const snowPath = result.stdout.toString().trim();
            return {
                name: 'Snow CLI available',
                passed: true,
                message: snowPath,
            };
        }
        return {
            name: 'Snow CLI available',
            passed: false,
            message: 'Not found in PATH',
            hint: 'Install the Snowflake CLI: https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation',
        };
    } catch {
        return {
            name: 'Snow CLI available',
            passed: false,
            message: 'Could not check for snow CLI',
            hint: 'Install the Snowflake CLI: https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation',
        };
    }
}

export function formatCheckResult(result: CheckResult): string {
    const icon = result.passed ? '✓' : '✗';
    let output = `  ${icon} ${result.name}: ${result.message}`;
    if (!result.passed && result.hint) {
        output += `\n    ${result.hint}`;
    }
    return output;
}

export async function runDoctorChecks(): Promise<CheckResult[]> {
    const results: CheckResult[] = [];

    // 1. CLI version
    results.push(await checkCliVersion());

    // 2. Connection config
    results.push(await checkConnection());

    // 3 & 4. Endpoint reachable + Controld healthy (need default connection endpoint)
    let endpoint: string | undefined;
    try {
        const config = new ConnectionConfig();
        const defaultName = config.getDefault();
        if (defaultName) {
            const conn = config.getConnection(defaultName);
            endpoint = conn?.endpoint;
        }
    } catch {
        // Connection config already checked above
    }

    if (endpoint) {
        results.push(await checkEndpointReachable(endpoint));
        results.push(await checkControldHealthy(endpoint));
    } else {
        results.push({
            name: 'Endpoint reachable',
            passed: false,
            message: 'No default connection configured',
            hint: 'Run "p67 connection add --set-default" to set a default connection.',
        });
        results.push({
            name: 'Controld healthy',
            passed: false,
            message: 'No default connection configured',
            hint: 'Run "p67 connection add --set-default" to set a default connection.',
        });
    }

    // 5. Snow CLI
    results.push(await checkSnowCli());

    return results;
}

export const doctorCommand = new Command('doctor')
    .description('Check the health of the P67 environment')
    .action(async () => {
        console.log('\nP67 Doctor\n');

        const results = await runDoctorChecks();

        for (const result of results) {
            console.log(formatCheckResult(result));
        }

        console.log('');

        const failed = results.some((r) => !r.passed);
        if (failed) {
            console.log('Some checks failed. See hints above for remediation.');
            process.exit(1);
        } else {
            console.log('All checks passed!');
        }
    });
