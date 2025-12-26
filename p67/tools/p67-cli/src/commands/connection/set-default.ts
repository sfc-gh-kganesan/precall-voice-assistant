import { Command } from '@p67-cli/Command';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';

export const setDefaultCommand = new Command('set-default')
	.description('Set the default connection')
	.argument('<name>', 'Connection name to set as default')
	.action(async (name: string) => {
		try {
			const config = new ConnectionConfig();
			const connection = config.getConnection(name);

			if (!connection) {
				throw new Error(
					`Connection "${name}" not found. Try "p67 connection list" to see available connections.`,
				);
			}

			config.setDefault(name);
			config.write();

			console.log(`\n✓ Default connection set to '${name}'`);
		} catch (error) {
			console.error(`Failed to set default connection (${name})`);
			throw error;
		}
	});
