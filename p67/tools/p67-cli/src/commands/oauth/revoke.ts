import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const revokeCommand = new Command('revoke')
    .description('Revoke (delete) an OAuth secret')
    .argument('<name>', 'Name of the OAuth secret to revoke')
    .option('--force', 'Skip confirmation prompt')
    .action(async (name: string, options: { force?: boolean }) => {
        try {
            const { connection } = ctx();

            // Confirmation prompt unless --force is used
            if (!options.force) {
                const readline = await import('node:readline');
                const rl = readline.createInterface({
                    input: process.stdin,
                    output: process.stdout,
                });

                const answer = await new Promise<string>((resolve) => {
                    rl.question(
                        `Are you sure you want to revoke OAuth secret '${name}'? (y/N) `,
                        resolve,
                    );
                });
                rl.close();

                if (answer.toLowerCase() !== 'y') {
                    console.log('Cancelled.');
                    return;
                }
            }

            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });

            const result = await client.deleteSecret(name);

            if (result.deleted) {
                console.log(`✓ OAuth secret '${name}' has been revoked.`);
                console.log(
                    '\nNote: This only removes the token from P67. You may also want to',
                );
                console.log(
                    "revoke access in the provider's settings (e.g., GitHub > Settings > Applications).",
                );
            } else {
                console.log(`Secret '${name}' not found.`);
            }
        } catch (error) {
            console.error('Failed to revoke OAuth secret');
            throw error;
        }
    });
