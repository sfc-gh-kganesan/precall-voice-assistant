/**
 * Utilities for interacting with the Snowflake CLI (`snow`).
 */

/**
 * Checks whether the `snow` CLI is available in PATH.
 */
export function isSnowInstalled(): boolean {
    try {
        const proc = Bun.spawnSync(['snow', '--version'], {
            stdout: 'pipe',
            stderr: 'pipe',
        });
        return proc.exitCode === 0;
    } catch {
        return false;
    }
}

/**
 * Runs `snow sql` to call P67.V1.APP_URL() and parses the endpoint URL
 * from the JSON output.
 *
 * @param snowConnection - Optional Snowflake connection name to pass via `-c`.
 * @returns The discovered endpoint URL.
 * @throws If `snow` is not installed, the query fails, or the output cannot be parsed.
 */
export async function discoverEndpoint(
    snowConnection?: string,
): Promise<string> {
    if (!isSnowInstalled()) {
        throw new Error(
            'The `snow` CLI is not installed or not in PATH. Install it from https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation',
        );
    }

    const args = [
        'snow',
        'sql',
        '-q',
        'CALL P67.V1.APP_URL()',
        '--format',
        'json',
    ];

    if (snowConnection) {
        args.push('-c', snowConnection);
    }

    const proc = Bun.spawn(args, {
        stdout: 'pipe',
        stderr: 'pipe',
    });

    const exitCode = await proc.exited;
    const stdout = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();

    if (exitCode !== 0) {
        throw new Error(`snow sql failed: ${stderr.trim() || stdout.trim()}`);
    }

    return parseEndpointFromOutput(stdout);
}

/**
 * Parses the endpoint URL from `snow sql --format json` output.
 *
 * The output is expected to be a JSON array of row objects, e.g.:
 * ```json
 * [{"P67.V1.APP_URL()": "https://example.snowflakecomputing.app"}]
 * ```
 */
export function parseEndpointFromOutput(output: string): string {
    let parsed: unknown;
    try {
        parsed = JSON.parse(output);
    } catch {
        throw new Error(`Failed to parse snow sql output as JSON: ${output}`);
    }

    if (!Array.isArray(parsed) || parsed.length === 0) {
        throw new Error(
            `Unexpected snow sql output format (expected non-empty array): ${output}`,
        );
    }

    const row = parsed[0];
    if (typeof row !== 'object' || row === null) {
        throw new Error(`Unexpected row format in snow sql output: ${output}`);
    }

    // The column name may vary — take the first value from the first row.
    const values = Object.values(row as Record<string, unknown>);
    if (values.length === 0) {
        throw new Error(`No columns in snow sql output row: ${output}`);
    }

    const url = values[0];
    if (typeof url !== 'string' || !url.trim()) {
        throw new Error(
            `Expected a URL string from snow sql output, got: ${JSON.stringify(url)}`,
        );
    }

    let trimmed = url.trim();

    // APP_URL() may return a bare hostname without protocol — normalise it.
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
        trimmed = `https://${trimmed}`;
    }

    // Basic URL validation
    try {
        new URL(trimmed);
    } catch {
        throw new Error(`Discovered value is not a valid URL: ${url}`);
    }

    return trimmed;
}
