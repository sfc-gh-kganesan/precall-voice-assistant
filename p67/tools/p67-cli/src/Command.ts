import { Command as CommanderCommand } from 'commander';

export class Command extends CommanderCommand {
    use<T>(fn: (cmd: Command, opts?: T) => Command, opts?: T): Command {
        return fn(this, opts);
    }
}
