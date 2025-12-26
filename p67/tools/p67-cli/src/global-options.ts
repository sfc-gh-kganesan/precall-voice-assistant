import type { Command } from 'commander';

export interface GlobalOptions {
	project: string;
}

export function options(command: Command): void {
	command.option(
		'-p, --project <path>',
		'Target project directory',
		process.cwd(),
	);
}
