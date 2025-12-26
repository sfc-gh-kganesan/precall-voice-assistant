import { confirm } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';

export const removeCommand = new Command('remove')
	.description('Remove a connection')
	.argument('<name>', 'Connection name to remove')
	.option('-y, --yes', 'Skip confirmation prompt')
	.action(async (name: string, options?: { yes?: boolean }) => {
		try {
			const config = new ConnectionConfig();
			const connection = config.getConnection(name);

			if (!connection) {
				console.error(`✗ Error: Connection '${name}' not found`);
				process.exit(1);
			}

			// Confirm removal unless -y flag is provided
			if (!options?.yes) {
				const confirmed = await confirm({
					message: `Remove connection '${name}'?`,
					default: false,
				});

				if (!confirmed) {
					console.log('Cancelled.');
					return;
				}
			}

			const wasDefault = config.getDefault() === name;

			config.removeConnection(name);
			config.write();

			console.log(`\n✓ Connection '${name}' removed successfully!`);
			if (wasDefault) {
				console.log('  Note: This was the default connection.');
				const remaining = config.getConnections();
				if (remaining.length > 0) {
					console.log(
						`  Run "p67 connection set-default <name>" to set a new default.`,
					);
				}
			}
		} catch (error) {
			console.error(`Failed to remove connection ${name}`);
			throw error;
		}
	});
