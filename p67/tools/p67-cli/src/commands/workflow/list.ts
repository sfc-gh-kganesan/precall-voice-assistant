import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const listCommand = new Command('list')
	.description('List all available workflows')
	.action(async () => {
		try {
			const { connection } = ctx();
			const client = new ControldClient({
				baseUrl: connection.endpoint,
				pat: connection.pat,
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
			console.error('Error listing workflows');
			throw error;
		}
	});
