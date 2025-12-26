import { select } from '@inquirer/prompts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import type { ConnectionEnabledCommand } from '@p67-cli/middleware/connection';
import { Command } from 'commander';

export const runCommand = new Command('run')
	.description('Run a workflow')
	.argument('[workflowId]', 'Workflow ID to run')
	.action(async (workflowId?: string) => {
		try {
			const connection = (runCommand.parent as ConnectionEnabledCommand)
				?.connection;

			const client = new ControldClient({
				baseUrl: connection?.endpoint ?? '',
				pat: connection?.pat ?? '',
			});

			let selectedWorkflowId = workflowId;

			// If no workflow ID provided, prompt user to select one
			if (!selectedWorkflowId) {
				console.log('Fetching available workflows...\n');
				const result = await client.listWorkflows();

				if (result.workflows.length === 0) {
					console.error('✗ Error: No workflows found');
					process.exit(1);
				}

				selectedWorkflowId = await select({
					message: 'Select a workflow to run:',
					choices: result.workflows.map((wf) => ({
						value: wf,
						name: wf,
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

			if (runResult.stdout) {
				console.log('\nStdout:');
				console.log(runResult.stdout);
			}

			if (runResult.stderr) {
				console.log('\nStderr:');
				console.error(runResult.stderr);
			}

			// Exit with the workflow's exit code
			process.exit(runResult.exitCode);
		} catch (error) {
			if (error instanceof Error) {
				console.error('✗ Error:', error.message);
			} else {
				console.error('✗ Unexpected error:', error);
			}
			process.exit(1);
		}
	});
