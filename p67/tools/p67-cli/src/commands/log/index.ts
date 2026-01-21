import { Command } from '@p67-cli/Command.ts';
import { connection } from '@p67-cli/middleware/connection';
import { projectConfig } from '@p67-cli/middleware/project-config';
import { listCommand } from './list.ts';

export const logsCommand = new Command('logs')
    .description('Manage workflow logs')
    .use(connection)
    .use(projectConfig)
    .addCommand(listCommand);
