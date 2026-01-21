import { Command } from '@p67-cli/Command';
import { deleteCommand } from '@p67-cli/commands/secret/delete.ts';
import { listCommand } from '@p67-cli/commands/secret/list.ts';
import { saveCommand } from '@p67-cli/commands/secret/save.ts';
import { connection } from '@p67-cli/middleware/connection';

export const secretCommand = new Command('secret')
    .description('Manage secrets')
    .use(connection)
    .addCommand(saveCommand)
    .addCommand(listCommand)
    .addCommand(deleteCommand);
