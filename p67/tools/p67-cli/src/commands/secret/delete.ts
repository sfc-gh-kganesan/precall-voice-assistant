import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const deleteCommand = new Command('delete')
    .description('Delete a secret by name')
    .argument('<name>', 'Name of the secret to delete')
    .action(async (name: string) => {
        try {
            const { connection } = ctx();

            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });

            const result = await client.deleteSecret(name);

            if (result.deleted) {
                console.log(`✓ Secret '${result.name}' deleted successfully`);
            }
        } catch (error) {
            console.error('Failed to delete secret');
            throw error;
        }
    });
