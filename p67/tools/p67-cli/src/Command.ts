import { Command as CommanderCommand } from 'commander';

export class Command extends CommanderCommand {
	use(fn: (cmd: Command) => Command): Command {
		return fn(this);
	}
}
