import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const listCommand = new Command('list')
    .description('List all secrets (names only)')
    .action(async () => {
        try {
            const { connection } = ctx();

            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });

            const result = await client.listSecrets();

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
