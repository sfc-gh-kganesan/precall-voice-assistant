import { Command } from 'commander';
import { listCommand } from '@p67-cli/commands/workflow/list.ts';
import { runCommand } from '@p67-cli/commands/workflow/run.ts';
import { deployCommand } from '@p67-cli/commands/workflow/deploy.ts';

export const workflowCommand = new Command('workflow')
  .description('Operate on workflows')
  .addCommand(listCommand)
  .addCommand(runCommand)
  .addCommand(deployCommand);
