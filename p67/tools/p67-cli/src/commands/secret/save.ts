import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

async function readStdin(): Promise<string> {
    const chunks: Buffer[] = [];

    return new Promise((resolve, reject) => {
        process.stdin.on('data', (chunk) => {
            chunks.push(Buffer.from(chunk));
        });

        process.stdin.on('end', () => {
            const input = Buffer.concat(chunks).toString('utf-8').trim();
            resolve(input);
        });

        process.stdin.on('error', reject);
    });
}

export const saveCommand = new Command('save')
    .description('Save a secret (reads value from stdin)')
    .argument('<name>', 'Name of the secret')
    .action(async (name: string) => {
        try {
            const { connection } = ctx();

            // Check if stdin is a TTY (interactive terminal)
            if (process.stdin.isTTY) {
                console.log('Enter secret value (press Ctrl+D when done):');
            }

            const secret = await readStdin();

            if (!secret) {
                throw new Error(
                    'No secret value provided. Pipe a value or enter it interactively.',
                );
            }

            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });

            const result = await client.saveSecret(name, secret);

            if (result.created) {
                console.log(`✓ Secret '${result.name}' created successfully`);
            } else {
                console.log(`✓ Secret '${result.name}' updated successfully`);
            }
        } catch (error) {
            console.error('Failed to save secret');
            throw error;
        }
    });
