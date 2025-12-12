#!/usr/bin/env bun
import { Command } from 'commander';
import { initCommand } from './commands/init.ts';
import { workflowCommand } from './commands/workflow.ts';
import { envCommand } from './commands/env.ts';

const VERSION = '0.1.0';

const program = new Command();

program
  .name('p67')
  .version(VERSION)
  .description('Project 67 Agentic Workflow Builder commands')
  .option('--cwd <path>', 'Target project directory', process.cwd());

program.addCommand(initCommand);
program.addCommand(envCommand);
program.addCommand(workflowCommand);

program.parse(process.argv);
