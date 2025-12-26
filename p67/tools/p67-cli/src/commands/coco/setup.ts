import { Command } from '@p67-cli/Command';
import { CocoCommands } from '@p67-cli/coco/CocoCommands';
import { ctx } from '@p67-cli/context';

export const setupCommand = new Command('setup')
	.description('Coco setup')
	.action(async () => {
		const mgr = new CocoCommands(ctx().projectConfig.projectDir);
		mgr.installCommands();
	});
