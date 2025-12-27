import { input } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';

export const addCommand = new Command('add')
    .description('Add a new P67 connection')
    .argument('[name]', 'Connection name')
    .option('-e, --endpoint <url>', 'Runtime endpoint URL')
    .option('-p, --pat <token>', 'Snowflake Programmatic Access Token (PAT)')
    .option('--set-default', 'Set as default connection')
    .action(
        async (
            name?: string,
            options?: {
                endpoint?: string;
                pat?: string;
                setDefault?: boolean;
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

                // Prompt for endpoint if not provided
                const endpoint =
                    options?.endpoint ||
                    (await input({
                        message: 'Runtime endpoint URL:',
                        default:
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
