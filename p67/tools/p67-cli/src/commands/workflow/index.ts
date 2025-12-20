import { deployCommand } from '@p67-cli/commands/workflow/deploy.ts';
import { listCommand } from '@p67-cli/commands/workflow/list.ts';
import { runCommand } from '@p67-cli/commands/workflow/run.ts';
import { Command } from 'commander';

export const workflowCommand = new Command('workflow')
	.description('Operate on workflows')
	.addCommand(listCommand)
	.addCommand(runCommand)
	.addCommand(deployCommand);
