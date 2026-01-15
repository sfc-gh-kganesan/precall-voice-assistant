import { select } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { DotP67Config } from '@p67-cli/config/DotP67Config.ts';
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

                const dotP67Config = new DotP67Config('.');

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
                    const choices = result.workflows.map((wf) => ({
                        value: wf.workflowId,
                        updatedAt: wf.updatedAt,
                        name: `${wf.workflowId} (${wf.updatedAt}, owner: ${wf.owner})`,
                    }));
                    // Sort the choices by updatedAt descending
                    choices.sort(
                        (a, b) =>
                            new Date(b.updatedAt).getTime() -
                            new Date(a.updatedAt).getTime(),
                    );
                    // If there's a workflowid in the dotP67Config, sort such that it's first.
                    if (dotP67Config.get().workflowId) {
                        choices.sort((a, _b) =>
                            a.value === dotP67Config.get().workflowId ? -1 : 1,
                        );
                    }
                    selectedWorkflowId = await select({
                        message: 'Select a workflow to run:',
                        choices: choices,
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
