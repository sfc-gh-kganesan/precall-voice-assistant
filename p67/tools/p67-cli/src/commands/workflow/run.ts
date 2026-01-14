import { select } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const runCommand = new Command('run')
    .description('Run a workflow')
    .argument('[workflowId]', 'Workflow ID to run')
    .option('-t, --timeout <ms>', 'Request timeout in milliseconds', '600000')
    .action(
        async (
            workflowId: string | undefined,
            options: { timeout: string },
        ) => {
            try {
                const { connection } = ctx();

                const client = new ControldClient({
                    baseUrl: connection.endpoint,
                    pat: connection.pat,
                    timeout: Number.parseInt(options.timeout, 10),
                });

                let selectedWorkflowId = workflowId;

                // If no workflow ID provided, prompt user to select one
                if (!selectedWorkflowId) {
                    console.log('Fetching available workflows...\n');
                    const result = await client.listWorkflows();

                    if (result.workflows.length === 0) {
                        throw new Error('No workflows found');
                    }

                    selectedWorkflowId = await select({
                        message: 'Select a workflow to run:',
                        choices: result.workflows.map((wf) => ({
                            value: wf.workflowId,
                            name: `${wf.workflowId} (${wf.updatedAt})`,
                        })),
                    });
                }

                console.log(`\nRunning workflow: ${selectedWorkflowId}\n`);

                const runResult = await client.runWorkflow(selectedWorkflowId);

                // Display results
                console.log('─'.repeat(50));
                console.log(`Exit Code: ${runResult.exitCode}`);
                console.log(`Success: ${runResult.success}`);
                console.log('─'.repeat(50));
                console.log(runResult.log.join('\n'));

                // Exit with the workflow's exit code
                process.exit(runResult.exitCode);
            } catch (error) {
                console.error('Failed to run workflow');
                throw error;
            }
        },
    );
