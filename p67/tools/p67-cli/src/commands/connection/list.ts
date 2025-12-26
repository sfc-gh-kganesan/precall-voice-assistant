import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';
import { Command } from 'commander';

export const listCommand = new Command('list')
	.description('List all P67 connections')
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
			if (error instanceof Error) {
				console.error('✗ Error:', error.message);
			} else {
				console.error('✗ Unexpected error:', error);
			}
			process.exit(1);
		}
	});
