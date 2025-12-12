import { Command } from 'commander';
import { listCommand } from './list.ts';

export const workflowCommand = new Command('workflow')
  .description('Operate on workflows')
  .addCommand(listCommand)
  .action(async () => {
    console.log('Not implemented.');
  });
