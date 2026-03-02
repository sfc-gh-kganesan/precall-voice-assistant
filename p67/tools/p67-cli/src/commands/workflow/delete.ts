import { confirm } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import { ControldClient } from '@p67-cli/clients/ControldClient';
import { ctx } from '@p67-cli/context';

export const deleteCommand = new Command('delete')
    .description('Delete a deployed workflow')
    .argument('<workflowId>', 'ID of the workflow to delete')
    .option('-y, --yes', 'Skip confirmation prompt')
    .action(async (workflowId: string, options?: { yes?: boolean }) => {
        const connection = ctx().connection;
        const client = new ControldClient({
            baseUrl: connection.endpoint,
            pat: connection.pat,
        });

        if (!options?.yes) {
            const confirmed = await confirm({
                message: `Delete workflow '${workflowId}'? This will remove all associated files, runs, and logs.`,
                default: false,
            });

            if (!confirmed) {
                console.log('Cancelled.');
                return;
            }
        }

        try {
            const result = await client.deleteWorkflow(workflowId);
            if (result.deleted) {
                console.log(
                    `\n✓ Workflow '${workflowId}' deleted successfully.`,
                );
            }
        } catch (error) {
            console.error(
                `Failed to delete workflow '${workflowId}':`,
                error instanceof Error ? error.message : error,
            );
            process.exit(1);
        }
    });
