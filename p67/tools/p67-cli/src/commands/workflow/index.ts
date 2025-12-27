import { Command } from '@p67-cli/Command';
import { deployCommand } from '@p67-cli/commands/workflow/deploy.ts';
import { listCommand } from '@p67-cli/commands/workflow/list.ts';
import { runCommand } from '@p67-cli/commands/workflow/run.ts';
import { connection } from '@p67-cli/middleware/connection';
import { projectConfig } from '@p67-cli/middleware/project-config';

export const workflowCommand = new Command('workflow')
    .description('Operate on workflows')
    .use(connection)
    .use(projectConfig)
    .addCommand(listCommand)
    .addCommand(runCommand)
    .addCommand(deployCommand);
