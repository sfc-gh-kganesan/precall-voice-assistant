import { Command } from '@p67-cli/Command';
import { addCommand } from '@p67-cli/commands/connection/add';
import { listCommand } from '@p67-cli/commands/connection/list';
import { removeCommand } from '@p67-cli/commands/connection/remove';
import { setDefaultCommand } from '@p67-cli/commands/connection/set-default';

export const connectionCommand = new Command('connection')
    .description('Manage connections')
    .addCommand(listCommand)
    .addCommand(addCommand)
    .addCommand(removeCommand)
    .addCommand(setDefaultCommand);
