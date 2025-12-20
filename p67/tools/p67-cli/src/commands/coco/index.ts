import { setupCommand } from '@p67-cli/commands/coco/setup.ts';
import { Command } from 'commander';

export const cocoCommand = new Command('coco')
	.description('Coco setup')
	.addCommand(setupCommand);
