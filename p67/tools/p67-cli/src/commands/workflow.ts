import { Command } from 'commander';

export const workflowCommand = new Command('workflow')
  .description('Operate on workflows')
  .action(async () => {
    console.log('Not implemented.');
  });
