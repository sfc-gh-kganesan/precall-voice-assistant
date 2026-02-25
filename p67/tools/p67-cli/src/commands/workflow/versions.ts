import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const versionsCommand = new Command('versions')
    .description('List all versions of a workflow by name')
    .argument('<name>', 'Workflow name to list versions for')
    .action(async (name: string) => {
        try {
            const { connection } = ctx();
            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });

            const result = await client.getWorkflowVersions(name);

            if (result.workflows.length === 0) {
                console.log(`No versions found for workflow "${name}".`);
            } else {
                console.log(
                    `Versions of workflow "${name}" (${result.workflows.length} total):\n`,
                );
                result.workflows.forEach((workflow, index) => {
                    const isLatest = index === 0 ? ' (latest)' : '';
                    console.log(`  ${workflow.workflowId}${isLatest}`);
                    console.log(
                        `    Created: ${workflow.createdAt}, Owner: ${workflow.owner}, Visibility: ${workflow.visibility}`,
                    );
                });
            }
        } catch (error) {
            console.error(`Error listing versions for workflow "${name}"`);
            throw error;
        }
    });
