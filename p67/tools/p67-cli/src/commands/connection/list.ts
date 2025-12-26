import { Command } from '@p67-cli/Command';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';

export const listCommand = new Command('list')
	.description('List all connections')
	.action(async () => {
		try {
			const config = new ConnectionConfig();
			const connections = config.getConnections();
			const defaultConn = config.getDefault();

			if (connections.length === 0) {
				console.log('No connections configured.');
				console.log(`\nRun "p67 connection add" to add a connection.`);
				return;
			}

			console.log('\nConfigured connections:\n');

			for (const conn of connections) {
				const isDefault = conn.name === defaultConn;
				const marker = isDefault ? '* ' : '  ';
				console.log(`${marker}${conn.name}`);
				console.log(`  Endpoint: ${conn.endpoint}`);
				if (isDefault) {
					console.log('  (default)');
				}
				console.log('');
			}

			console.log(`Configuration file: ${config.getConfigPath()}`);
		} catch (error) {
			console.error('Failed to list connections');
			throw error;
		}
	});
