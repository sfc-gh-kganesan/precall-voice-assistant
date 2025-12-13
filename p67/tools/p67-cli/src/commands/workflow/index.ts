import { Command } from 'commander';
import { listCommand } from './list.ts';
import { runCommand } from './run.ts';
import { deployCommand } from './deploy.ts';

export const workflowCommand = new Command('workflow')
  .description('Operate on workflows')
  .addCommand(listCommand)
  .addCommand(runCommand)
  .addCommand(deployCommand)
  .action(async () => {
    console.log('Not implemented.');
  });
