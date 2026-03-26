import { input } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';
import { discoverEndpoint } from '@p67-cli/utils/snow-cli';

export const addCommand = new Command('add')
    .description('Add a new P67 connection')
    .argument('[name]', 'Connection name')
    .option('-e, --endpoint <url>', 'Runtime endpoint URL')
    .option('-p, --pat <token>', 'Snowflake Programmatic Access Token (PAT)')
    .option('--set-default', 'Set as default connection')
    .option(
        '--discover',
        'Auto-discover the endpoint URL via snow sql (calls P67.V1.APP_URL())',
    )
    .option(
        '--snow-connection <name>',
        'Snowflake connection name to use with snow CLI (for --discover)',
    )
    .action(
        async (
            name?: string,
            options?: {
                endpoint?: string;
                pat?: string;
                setDefault?: boolean;
                discover?: boolean;
                snowConnection?: string;
            },
        ) => {
            try {
                const config = new ConnectionConfig();

                // Prompt for name if not provided
                const connectionName =
                    name ||
                    (await input({
                        message: 'Connection name:',
                        validate: (value) => {
                            if (!value.trim()) {
                                return 'Connection name is required';
                            }
                            if (config.getConnection(value.trim())) {
                                return `Connection '${value.trim()}' already exists`;
                            }
                            return true;
                        },
                    }));

                // Discover endpoint if --discover is passed
                let discoveredEndpoint: string | undefined;
                if (options?.discover) {
                    try {
                        console.log('Discovering endpoint via snow sql...');
                        discoveredEndpoint = await discoverEndpoint(
                            options.snowConnection,
                        );
                        console.log(
                            `Discovered endpoint: ${discoveredEndpoint}`,
                        );
                    } catch (error) {
                        console.error(
                            `\nFailed to discover endpoint: ${error instanceof Error ? error.message : error}`,
                        );
                        console.log(
                            'Falling back to manual endpoint prompt.\n',
                        );
                    }
                }

                // Prompt for endpoint if not provided via --endpoint flag.
                // If --discover found a URL, use it as the default (user can override).
                const endpoint =
                    options?.endpoint ||
                    (await input({
                        message: 'Runtime endpoint URL:',
                        default:
                            discoveredEndpoint ??
                            'https://jnb46h6e-sfengineering-aifde.snowflakecomputing.app',
                        validate: (value) => {
                            if (!value.trim()) {
                                return 'Endpoint is required';
                            }
                            try {
                                new URL(value.trim());
                                return true;
                            } catch {
                                return 'Invalid URL';
                            }
                        },
                    }));

                // Prompt for PAT if not provided
                const pat =
                    options?.pat ||
                    (await input({
                        message: 'Snowflake PAT:',
                        validate: (value) => {
                            if (!value.trim()) {
                                return 'PAT is required';
                            }
                            return true;
                        },
                    }));

                // Add the connection
                config.addConnection({
                    name: connectionName.trim(),
                    endpoint: endpoint.trim(),
                    pat: pat.trim(),
                });

                // Set as default if requested or if it's the first connection
                if (
                    options?.setDefault ||
                    config.getConnections().length === 1
                ) {
                    config.setDefault(connectionName.trim());
                }

                config.write();

                console.log(
                    `\n✓ Connection '${connectionName}' added successfully!`,
                );
                if (config.getDefault() === connectionName.trim()) {
                    console.log('  (set as default)');
                }
                console.log(
                    `\nConfiguration saved to: ${config.getConfigPath()}`,
                );
            } catch (error) {
                console.error('Failed to add connection');
                throw error;
            }
        },
    );
