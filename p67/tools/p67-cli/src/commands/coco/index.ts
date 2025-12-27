import { Command } from '@p67-cli/Command.ts';
import { setupCommand } from '@p67-cli/commands/coco/setup.ts';
import { projectConfig } from '@p67-cli/middleware/project-config';

export const cocoCommand = new Command('coco')
    .description('Coco setup')
    .use(projectConfig)
    .addCommand(setupCommand);
