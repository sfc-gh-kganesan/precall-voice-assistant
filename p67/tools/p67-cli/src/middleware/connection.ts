import type { Command } from '@p67-cli/Command';
import { ConnectionConfig } from '@p67-cli/config/ConnectionConfig';
import { ctx } from '@p67-cli/context';

export interface ConnectionOptions {
	connection: string;
}

export function connection(command: Command): Command {
	const connectionConfig = new ConnectionConfig();
	const defaultConnection = connectionConfig.getDefault();
	return command
		.option(
			'-c, --connection <connection>',
			'P67 connection',
			defaultConnection,
		)
		.hook('preAction', (action) => {
			const options = action.optsWithGlobals<ConnectionOptions>();

			if (!connectionConfig.exists()) {
				throw new Error(
					'No connections are configured. Run "p67 connection add"',
				);
			}

			const connection = connectionConfig.getConnection(options.connection);

			if (!connection) {
				throw new Error(
					`Connection ${options.connection} does not specify an endpoint value.`,
				);
			}

			if (!connection.pat) {
				throw new Error(
					`Connection ${options.connection} does not specify a pat value.`,
				);
			}

			ctx().connectionConfig = connectionConfig;
			ctx().connection = connection;
		});
}
