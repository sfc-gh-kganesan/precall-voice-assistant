import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const listCommand = new Command('list')
    .description('List all secrets (excluding OAuth tokens)')
    .option('--all', 'Include OAuth tokens in the list')
    .action(async (options: { all?: boolean }) => {
        try {
            const { connection } = ctx();

            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });

            // Filter to only regular secrets unless --all is specified
            const result = await client.listSecrets(
                options.all ? undefined : 'Secret',
            );

            if (result.secrets.length === 0) {
                console.log('No secrets found.');
            } else {
                for (const secret of result.secrets) {
                    console.log(
                        `${secret.name} (created: ${secret.createdAt}, updated: ${secret.updatedAt})`,
                    );
                }
            }
        } catch (error) {
            console.error('Failed to list secrets');
            throw error;
        }
    });
