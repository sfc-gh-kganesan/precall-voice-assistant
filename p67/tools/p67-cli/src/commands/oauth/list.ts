import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const listCommand = new Command('list')
    .description('List OAuth tokens')
    .action(async () => {
        try {
            const { connection } = ctx();

            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });

            const result = await client.listSecrets('OAuth');

            if (result.secrets.length === 0) {
                console.log('No OAuth tokens found.');
                console.log(
                    '\nUse "p67 oauth connect <provider> --secret-name=<name>" to create one.',
                );
                return;
            }

            console.log('OAuth tokens:\n');
            console.log(
                'NAME                          CREATED              UPDATED',
            );
            console.log(
                '────────────────────────────  ───────────────────  ───────────────────',
            );

            for (const secret of result.secrets) {
                const name = secret.name.padEnd(28);
                const created = new Date(secret.createdAt)
                    .toISOString()
                    .slice(0, 19)
                    .replace('T', ' ');
                const updated = new Date(secret.updatedAt)
                    .toISOString()
                    .slice(0, 19)
                    .replace('T', ' ');
                console.log(`${name}  ${created}  ${updated}`);
            }

            console.log(
                '\nUse "p67 oauth connect <provider> --secret-name=<name>" to add/update OAuth tokens.',
            );
        } catch (error) {
            console.error('Failed to list OAuth tokens');
            throw error;
        }
    });
