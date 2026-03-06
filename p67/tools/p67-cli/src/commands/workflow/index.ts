import { Command } from '@p67-cli/Command';
import { deleteCommand } from '@p67-cli/commands/workflow/delete.ts';
import { deployCommand } from '@p67-cli/commands/workflow/deploy.ts';
import { listCommand } from '@p67-cli/commands/workflow/list.ts';
import { runCommand } from '@p67-cli/commands/workflow/run.ts';
import { runsCommand } from '@p67-cli/commands/workflow/runs.ts';
import { versionsCommand } from '@p67-cli/commands/workflow/versions.ts';
import { connection } from '@p67-cli/middleware/connection';

export const workflowCommand = new Command('workflow')
    .description('Operate on workflows')
    .use(connection)
    .addCommand(listCommand)
    .addCommand(runCommand)
    .addCommand(runsCommand)
    .addCommand(deployCommand)
    .addCommand(versionsCommand)
    .addCommand(deleteCommand);
