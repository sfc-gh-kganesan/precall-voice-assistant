import { confirm } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import { ControldClient } from '@p67-cli/clients/ControldClient';
import { ctx } from '@p67-cli/context';

export const cancelRunCommand = new Command('cancel-run')
    .description('Cancel a running or stuck workflow run')
    .argument('<runId>', 'ID of the run to cancel')
    .option('-y, --yes', 'Skip confirmation prompt')
    .action(async (runId: string, options?: { yes?: boolean }) => {
        const connection = ctx().connection;
        const client = new ControldClient({
            baseUrl: connection.endpoint,
            pat: connection.pat,
        });

        if (!options?.yes) {
            const confirmed = await confirm({
                message: `Cancel run '${runId}'?`,
                default: false,
            });

            if (!confirmed) {
                console.log('Cancelled.');
                return;
            }
        }

        try {
            const result = await client.cancelRun(runId);
            if (result.cancelled) {
                console.log(`\nRun '${runId}' cancelled successfully.`);
            }
        } catch (error) {
            console.error(
                `Failed to cancel run '${runId}':`,
                error instanceof Error ? error.message : error,
            );
            process.exit(1);
        }
    });
