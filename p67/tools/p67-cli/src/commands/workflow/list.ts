import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import type { ConnectionEnabledCommand } from '@p67-cli/middleware/connection';
import { Command } from 'commander';

export const listCommand = new Command('list')
	.description('List all available workflows')
	.action(async () => {
		try {
			const connection = (listCommand.parent as ConnectionEnabledCommand)
				?.connection;
			const client = new ControldClient({
				baseUrl: connection?.endpoint ?? '',
				pat: connection?.pat ?? '',
			});
			const result = await client.listWorkflows();

			if (result.workflows.length === 0) {
				console.log('No workflows found.');
			} else {
				result.workflows.forEach((workflow) => {
					console.log(workflow);
				});
			}
		} catch (error) {
			if (error instanceof Error) {
				console.error('✗ Error:', error.message);
			} else {
				console.error('✗ Unexpected error:', error);
			}
			process.exit(1);
		}
	});
