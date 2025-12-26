#!/usr/bin/env bun
import { program } from '@p67-cli/program';

(async () => {
	try {
		await program.parseAsync(process.argv);
	} catch (err: unknown) {
		const error = err as Error;
		console.error(`Error: ${error.message}`);
		if (process.env.DEBUG) {
			console.error(error.stack);
		}
		process.exit(1);
	}
})();

process.on('unhandledRejection', (err) => {
	console.error('Unhandled rejection:', err);
	process.exit(1);
});
