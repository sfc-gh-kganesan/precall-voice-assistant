#!/usr/bin/env bun
import { buildCommand } from '@p67-cli/commands/build';
import { cocoCommand } from '@p67-cli/commands/coco/index';
import { connectionCommand } from '@p67-cli/commands/connection';
import { initCommand } from '@p67-cli/commands/init.ts';
import { workflowCommand } from '@p67-cli/commands/workflow';
import { options } from '@p67-cli/global-options';
import { Command } from 'commander';

const VERSION = '0.1.0';

const program = new Command('p67');

program
	.name('p67')
	.version(VERSION)
	.description('Project 67 Agentic Workflow Builder commands');

options(program);

program.addCommand(initCommand);
program.addCommand(workflowCommand);
program.addCommand(cocoCommand);
program.addCommand(buildCommand);
program.addCommand(connectionCommand);

program.parse(process.argv);
