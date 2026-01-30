import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { input, select } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import { ControldClient } from '@p67-cli/clients/ControldClient';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';
import {
    type ProjectConfigOptions,
    type ProjectOptions,
    projectConfig,
} from '@p67-cli/middleware/project-config';
import * as yaml from 'js-yaml';
import * as toml from 'toml';

interface SnowflakeConnection {
    account?: string;
    user?: string;
    authenticator?: string;
    host?: string;
    database?: string;
    schema?: string;
    warehouse?: string;
    role?: string;
    password?: string;
    token?: string;
    connection_timeout?: number;
}

interface SnowflakeConfig {
    connections?: Record<string, SnowflakeConnection>;
}

interface ManifestValue {
    value?: string;
    secretRef?: string;
}

interface ManifestConfigEntry {
    config_name: string;
    account?: ManifestValue;
    username?: ManifestValue;
    authenticator?: ManifestValue;
    accessUrl?: ManifestValue;
    database?: ManifestValue;
    schema?: ManifestValue;
    warehouse?: ManifestValue;
    role?: ManifestValue;
    token?: ManifestValue;
}

interface Manifest {
    config: ManifestConfigEntry[];
}

function getSnowflakeConfigPath(): string | null {
    const snowflakeDir = path.join(os.homedir(), '.snowflake');

    // Try connections.toml first
    const connectionsPath = path.join(snowflakeDir, 'connections.toml');
    if (fs.existsSync(connectionsPath)) {
        return connectionsPath;
    }

    // Fall back to config.toml
    const configPath = path.join(snowflakeDir, 'config.toml');
    if (fs.existsSync(configPath)) {
        return configPath;
    }

    return null;
}

function parseSnowflakeConfig(configPath: string): SnowflakeConfig {
    const content = fs.readFileSync(configPath, 'utf8');
    return toml.parse(content) as SnowflakeConfig;
}

interface PatResult {
    tokenName: string;
    tokenSecret: string;
}

async function createProgrammaticAccessToken(
    connectionName: string,
    tokenName: string,
    daysToExpiry: number,
): Promise<PatResult> {
    const sql = `ALTER USER ADD PROGRAMMATIC ACCESS TOKEN ${tokenName} DAYS_TO_EXPIRY = ${daysToExpiry}`;

    const proc = Bun.spawn(
        ['snow', 'sql', '-q', sql, '-c', connectionName, '--format', 'json'],
        {
            stdout: 'pipe',
            stderr: 'pipe',
        },
    );

    const exitCode = await proc.exited;
    const stdout = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();

    if (exitCode !== 0) {
        throw new Error(`Failed to create PAT: ${stderr || stdout}`);
    }

    // Parse the JSON output to extract token_name and token_secret
    try {
        const result = JSON.parse(stdout);
        // snow sql returns an array of rows
        if (Array.isArray(result) && result.length > 0) {
            const row = result[0];
            return {
                tokenName: row.token_name || row.TOKEN_NAME,
                tokenSecret: row.token_secret || row.TOKEN_SECRET,
            };
        }
        throw new Error('Unexpected response format from snow sql');
    } catch (_parseError) {
        // If JSON parsing fails, try to extract from text output
        throw new Error(`Failed to parse PAT response: ${stdout}`);
    }
}

function snowflakeToManifestEntry(
    name: string,
    conn: SnowflakeConnection,
    tokenSecretRef?: string,
): ManifestConfigEntry {
    const entry: ManifestConfigEntry = {
        config_name: name,
    };

    if (conn.account) {
        entry.account = { value: conn.account };
    }
    if (conn.user) {
        entry.username = { value: conn.user };
    }

    // If we have a token secretRef, use that instead of authenticator
    if (tokenSecretRef) {
        entry.token = { secretRef: tokenSecretRef };
        // Don't include externalbrowser authenticator when using PAT
    } else if (conn.authenticator) {
        entry.authenticator = { value: conn.authenticator };
    }

    if (conn.host) {
        entry.accessUrl = { value: conn.host };
    }
    if (conn.database) {
        entry.database = { value: conn.database };
    }
    if (conn.schema) {
        entry.schema = { value: conn.schema };
    }
    if (conn.warehouse) {
        entry.warehouse = { value: conn.warehouse };
    }
    if (conn.role) {
        entry.role = { value: conn.role };
    }

    return entry;
}

export const fromConnectionCommand = new Command('from-connection')
    .description(
        'Bootstrap manifest.yaml from an existing Snowflake connection',
    )
    .argument('[connection-name]', 'Name of the Snowflake connection to use')
    .option(
        '--no-pat',
        'Skip PAT creation prompt for externalbrowser connections',
    )
    .use<ProjectConfigOptions>(projectConfig, {
        requireConfigFileToExist: false,
    })
    .action(async (connectionName?: string, cmdOptions?: { pat?: boolean }) => {
        const options = fromConnectionCommand.optsWithGlobals<ProjectOptions>();
        const projectDir = path.resolve(options.project as string);
        const manifestPath = path.join(projectDir, 'manifest.yaml');
        const skipPat = cmdOptions?.pat === false;

        // Find Snowflake config file
        const configPath = getSnowflakeConfigPath();
        if (!configPath) {
            console.error(
                '✗ No Snowflake configuration found at ~/.snowflake/connections.toml or ~/.snowflake/config.toml',
            );
            process.exit(1);
        }

        console.log(`Using Snowflake config: ${configPath}`);

        // Parse the config
        let sfConfig: SnowflakeConfig;
        try {
            sfConfig = parseSnowflakeConfig(configPath);
        } catch (error) {
            console.error(`✗ Failed to parse ${configPath}:`, error);
            process.exit(1);
        }

        // Get available connections
        const connections = sfConfig.connections || {};
        const connectionNames = Object.keys(connections);

        if (connectionNames.length === 0) {
            console.error('✗ No connections found in Snowflake config');
            process.exit(1);
        }

        // Determine which connection to use
        let selectedName: string;

        if (connectionName) {
            // User specified a connection name
            if (!connections[connectionName]) {
                console.error(
                    `✗ Connection '${connectionName}' not found. Available: ${connectionNames.join(', ')}`,
                );
                process.exit(1);
            }
            selectedName = connectionName;
        } else if (connectionNames.length === 1) {
            // Only one connection, use it
            selectedName = connectionNames[0] as string;
        } else {
            // Multiple connections, prompt user to select
            selectedName = await select({
                message: 'Select a Snowflake connection:',
                choices: connectionNames.map((name) => {
                    const conn = connections[name];
                    return {
                        name: name,
                        value: name,
                        description: conn?.account
                            ? `Account: ${conn.account}`
                            : undefined,
                    };
                }),
            });
        }

        const selectedConnection = connections[selectedName];
        if (!selectedConnection) {
            console.error(`✗ Connection '${selectedName}' not found`);
            process.exit(1);
        }
        console.log(`\nUsing connection: ${selectedName}`);

        // Check if this is an externalbrowser connection and offer PAT creation
        let tokenSecretRef: string | undefined;
        const isExternalBrowser =
            selectedConnection.authenticator?.toLowerCase() ===
            'externalbrowser';

        if (isExternalBrowser && !skipPat) {
            console.log(
                '\nThis connection uses externalbrowser authentication.',
            );
            console.log(
                'For programmatic access, you need a token stored as a secret.',
            );

            // Try to get existing secrets
            let existingSecrets: string[] = [];
            let p67Client: ControldClient | null = null;

            try {
                const p67Config = new ConnectionConfig();
                const defaultConnName = p67Config.getDefault();
                const p67Connection = defaultConnName
                    ? p67Config.getConnection(defaultConnName)
                    : p67Config.getConnections()[0];

                if (p67Connection) {
                    p67Client = new ControldClient({
                        baseUrl: p67Connection.endpoint,
                        pat: p67Connection.pat,
                    });

                    const secretsResponse =
                        await p67Client.listSecrets('Secret');
                    existingSecrets = secretsResponse.secrets.map(
                        (s) => s.name,
                    );
                }
            } catch {
                // Ignore errors fetching secrets
            }

            // Build choices for the select prompt
            type TokenChoice = {
                name: string;
                value: string;
                description?: string;
            };

            const choices: TokenChoice[] = [
                {
                    name: 'Generate new PAT',
                    value: '__generate_pat__',
                    description:
                        'Create a new Programmatic Access Token via snow CLI',
                },
                {
                    name: 'Skip (use externalbrowser)',
                    value: '__skip__',
                    description: 'Keep externalbrowser auth in manifest',
                },
            ];

            // Add existing secrets as options
            if (existingSecrets.length > 0) {
                for (const secret of existingSecrets) {
                    choices.unshift({
                        name: secret,
                        value: secret,
                        description: 'Use existing secret',
                    });
                }
            }

            const tokenChoice = await select({
                message: 'Select a token secret or generate a new PAT:',
                choices,
            });

            if (tokenChoice === '__skip__') {
                // Do nothing, keep externalbrowser
            } else if (tokenChoice === '__generate_pat__') {
                // Generate a new PAT
                const tokenName = await input({
                    message: 'PAT name:',
                    default: `p67_${selectedName}_pat`,
                    validate: (value) => {
                        if (!value.trim()) {
                            return 'Token name is required';
                        }
                        if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value.trim())) {
                            return 'Token name must be a valid identifier (letters, numbers, underscores)';
                        }
                        return true;
                    },
                });

                const daysToExpiry = await input({
                    message: 'Days until expiry:',
                    default: '90',
                    validate: (value) => {
                        const num = Number.parseInt(value, 10);
                        if (Number.isNaN(num) || num < 1 || num > 365) {
                            return 'Must be a number between 1 and 365';
                        }
                        return true;
                    },
                });

                const secretName = await input({
                    message: 'Secret name to store the PAT:',
                    default: `${selectedName}_pat`,
                    validate: (value) => {
                        if (!value.trim()) {
                            return 'Secret name is required';
                        }
                        return true;
                    },
                });

                console.log('\nCreating PAT via snow CLI...');
                console.log('(This will open a browser for authentication)\n');

                try {
                    const patResult = await createProgrammaticAccessToken(
                        selectedName,
                        tokenName.trim(),
                        Number.parseInt(daysToExpiry, 10),
                    );

                    console.log(
                        `✓ PAT '${patResult.tokenName}' created successfully`,
                    );

                    // Try to save the token as a secret using ControldClient
                    console.log(`\nSaving PAT to secret '${secretName}'...`);

                    if (p67Client) {
                        try {
                            const result = await p67Client.saveSecret(
                                secretName.trim(),
                                patResult.tokenSecret,
                            );

                            if (result.created) {
                                console.log(
                                    `✓ Secret '${result.name}' created successfully`,
                                );
                            } else {
                                console.log(
                                    `✓ Secret '${result.name}' updated successfully`,
                                );
                            }
                            tokenSecretRef = secretName.trim();
                        } catch (saveError) {
                            console.error(
                                `\n⚠ Failed to save PAT to secret: ${saveError}`,
                            );
                            console.log(`  You can manually save it with:`);
                            console.log(
                                `  echo '${patResult.tokenSecret}' | p67 secret save ${secretName}`,
                            );
                        }
                    } else {
                        console.log(
                            `\n⚠ No P67 connection configured. Cannot save secret automatically.`,
                        );
                        console.log(
                            `  Run 'p67 connection add' first, then save the token with:`,
                        );
                        console.log(
                            `  echo '${patResult.tokenSecret}' | p67 secret save ${secretName}`,
                        );
                    }
                } catch (error) {
                    console.error(`\n✗ Failed to create PAT: ${error}`);
                    console.log('Continuing without PAT...\n');
                }
            } else {
                // User selected an existing secret
                tokenSecretRef = tokenChoice;
                console.log(`\nUsing existing secret: ${tokenChoice}`);
            }
        }

        // Convert to manifest entry
        const manifestEntry = snowflakeToManifestEntry(
            selectedName,
            selectedConnection,
            tokenSecretRef,
        );

        // Load existing manifest or create new one
        let manifest: Manifest;
        if (fs.existsSync(manifestPath)) {
            try {
                const content = fs.readFileSync(manifestPath, 'utf8');
                manifest = yaml.load(content) as Manifest;
                if (!manifest || !manifest.config) {
                    manifest = { config: [] };
                }
            } catch {
                manifest = { config: [] };
            }
        } else {
            manifest = { config: [] };
        }

        // Check if this config_name already exists
        const existingIndex = manifest.config.findIndex(
            (c) => c.config_name === selectedName,
        );

        if (existingIndex >= 0) {
            manifest.config[existingIndex] = manifestEntry;
            console.log(`Updated existing config entry: ${selectedName}`);
        } else {
            manifest.config.push(manifestEntry);
            console.log(`Added new config entry: ${selectedName}`);
        }

        // Write manifest
        try {
            const yamlContent = yaml.dump(manifest, {
                indent: 2,
                lineWidth: -1,
                quotingType: '"',
                forceQuotes: false,
            });
            fs.writeFileSync(manifestPath, yamlContent, 'utf8');
            console.log(`\n✓ Manifest written to: ${manifestPath}`);
        } catch (error) {
            console.error('✗ Failed to write manifest:', error);
            process.exit(1);
        }

        // Show what was added
        console.log('\nConfiguration added:');
        for (const [key, val] of Object.entries(manifestEntry)) {
            if (key === 'config_name') {
                console.log(`  ${key}: ${val}`);
            } else if (typeof val === 'object' && val !== null) {
                if ('value' in val && val.value) {
                    console.log(`  ${key}: ${val.value}`);
                } else if ('secretRef' in val && val.secretRef) {
                    console.log(`  ${key}: (secretRef: ${val.secretRef})`);
                }
            }
        }
    });
