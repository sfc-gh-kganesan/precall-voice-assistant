import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const refreshCommand = new Command('refresh')
    .description('Refresh an OAuth token')
    .argument('<name>', 'Name of the OAuth secret to refresh')
    .option(
        '--client-id <id>',
        'OAuth client ID (or set P67_OAUTH_CLIENT_ID env var)',
    )
    .option(
        '--client-secret <secret>',
        'OAuth client secret (or set P67_OAUTH_CLIENT_SECRET env var)',
    )
    .option('--force', 'Force refresh even if token is not expired')
    .action(
        async (
            name: string,
            options: {
                clientId?: string;
                clientSecret?: string;
                force?: boolean;
            },
        ) => {
            try {
                const { connection } = ctx();

                // Resolve client credentials
                const clientId =
                    options.clientId || process.env.P67_OAUTH_CLIENT_ID;
                const clientSecret =
                    options.clientSecret || process.env.P67_OAUTH_CLIENT_SECRET;

                if (!clientId) {
                    throw new Error(
                        'Client ID is required. Provide --client-id or set P67_OAUTH_CLIENT_ID env var.',
                    );
                }

                if (!clientSecret) {
                    throw new Error(
                        'Client secret is required. Provide --client-secret or set P67_OAUTH_CLIENT_SECRET env var.',
                    );
                }

                const client = new ControldClient({
                    baseUrl: connection.endpoint,
                    pat: connection.pat,
                });

                console.log(`Refreshing OAuth token '${name}'...`);

                const result = await client.refreshOAuthToken(
                    name,
                    clientId,
                    clientSecret,
                );

                if (result.refreshed) {
                    console.log(
                        `\n✓ OAuth token '${name}' refreshed successfully.`,
                    );
                    console.log(`  Provider: ${result.provider}`);
                    if (result.expiresAt) {
                        const expiresAt = new Date(result.expiresAt);
                        const now = new Date();
                        const diffMs = expiresAt.getTime() - now.getTime();
                        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                        const diffDays = Math.floor(diffHours / 24);

                        let expiryStr: string;
                        if (diffDays > 0) {
                            expiryStr = `in ${diffDays} day(s)`;
                        } else if (diffHours > 0) {
                            expiryStr = `in ${diffHours} hour(s)`;
                        } else {
                            expiryStr = 'soon';
                        }

                        console.log(
                            `  Expires: ${expiresAt.toISOString()} (${expiryStr})`,
                        );
                    } else {
                        console.log('  Expires: Never');
                    }
                } else {
                    console.log(
                        `\n✓ OAuth token '${name}' is still valid, no refresh needed.`,
                    );
                    console.log(`  Provider: ${result.provider}`);
                    if (result.expiresAt) {
                        console.log(`  Expires: ${result.expiresAt}`);
                    }
                }
            } catch (error) {
                console.error('Failed to refresh OAuth token');
                throw error;
            }
        },
    );
