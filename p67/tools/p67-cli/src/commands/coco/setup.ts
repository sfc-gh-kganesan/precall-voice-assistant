import { CocoCommands } from '@p67-cli/coco/CocoCommands';
import type { GlobalOptions } from '@p67-cli/global-options.ts';
import { Command } from 'commander';

export const setupCommand = new Command('setup')
	.description('Coco setup')
	.action(async () => {
		const options = setupCommand.optsWithGlobals<GlobalOptions>();
		const mgr = new CocoCommands(options.project);
		mgr.installCommands();
	});
