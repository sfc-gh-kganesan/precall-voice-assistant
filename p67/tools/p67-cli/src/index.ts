#!/usr/bin/env bun
import { cocoCommand } from '@p67-cli/commands/coco/index';
import { envCommand } from '@p67-cli/commands/env.ts';
import { initCommand } from '@p67-cli/commands/init.ts';
import { workflowCommand } from '@p67-cli/commands/workflow';
import { Command } from 'commander';

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
program.addCommand(cocoCommand);

program.parse(process.argv);
