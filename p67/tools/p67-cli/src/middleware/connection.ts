import type { Connection } from '@p67-cli/config/ConnectionConfig';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';
import { Command } from 'commander';

export interface ConnectionOptions {
	connection: string;
}

export class ConnectionEnabledCommand extends Command {
	connection?: Connection;
}

export function connectionMiddleware(command: ConnectionEnabledCommand): void {
	const defaultConnection = new ConnectionConfig().getDefault();
	command
		.option(
			'-c, --connection <connection>',
			`P67 connection (default: ${defaultConnection})`,
			defaultConnection,
		)
		.hook('preAction', (action) => {
			const options = action.optsWithGlobals<ConnectionOptions>();
			const config = new ConnectionConfig();

			if (!config.exists()) {
				console.error('✗ Error: No connections are configured.');
				console.error('  Run "p67 connection add"');
				process.exit(1);
			}

			const connection = config.getConnection(options.connection);

			if (!connection) {
				console.error(
					`Connection ${options.connection} does not specify an endpoint value.`,
				);
				process.exit(1);
			}

			if (!connection.pat) {
				console.error(
					`Connection ${options.connection} does not specify a pat value.`,
				);
				process.exit(1);
			}

			command.connection = connection;
		});
}
