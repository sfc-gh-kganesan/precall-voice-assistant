import { Command } from 'commander';
import { setupCommand } from '@p67-cli/commands/coco/setup.ts';

export const cocoCommand = new Command('coco').description('Coco setup').addCommand(setupCommand);
