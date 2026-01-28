import { Command } from '@p67-cli/Command.ts';
import { buildCommand } from '@p67-cli/commands/build';
import { cocoCommand } from '@p67-cli/commands/coco/index';
import { connectionCommand } from '@p67-cli/commands/connection';
import { createProjectRootCommand } from '@p67-cli/commands/createProjectRoot.ts';
import { initCommand } from '@p67-cli/commands/init.ts';
import { logsCommand } from '@p67-cli/commands/log';
import { oauthCommand } from '@p67-cli/commands/oauth';
import { secretCommand } from '@p67-cli/commands/secret';
import { workflowCommand } from '@p67-cli/commands/workflow';

const VERSION = '0.1.0';

export const program = new Command()
    .name('p67')
    .version(VERSION)
    .description('Project 67 -- Workflow Builder')
    .addCommand(initCommand)
    .addCommand(createProjectRootCommand)
    .addCommand(workflowCommand)
    .addCommand(logsCommand)
    .addCommand(secretCommand)
    .addCommand(oauthCommand)
    .addCommand(cocoCommand)
    .addCommand(buildCommand)
    .addCommand(connectionCommand);
