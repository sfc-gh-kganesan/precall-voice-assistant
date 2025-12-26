import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';
import { Command } from 'commander';

export const setDefaultCommand = new Command('set-default')
	.description('Set the default P67 connection')
	.argument('<name>', 'Connection name to set as default')
	.action(async (name: string) => {
		try {
			const config = new ConnectionConfig();
			const connection = config.getConnection(name);

			if (!connection) {
				console.error(`✗ Error: Connection '${name}' not found`);
				console.error(
					`\nRun "p67 connection list" to see available connections.`,
				);
				process.exit(1);
			}

			config.setDefault(name);
			config.write();

			console.log(`\n✓ Default connection set to '${name}'`);
		} catch (error) {
			if (error instanceof Error) {
				console.error('✗ Error:', error.message);
			} else {
				console.error('✗ Unexpected error:', error);
			}
			process.exit(1);
		}
	});
