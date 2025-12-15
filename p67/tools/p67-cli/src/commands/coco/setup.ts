import { CocoCommands } from '@p67-cli/coco/CocoCommands';
import { Command } from 'commander';

export const setupCommand = new Command('setup').description('Coco setup').action(async () => {
  const options = setupCommand.optsWithGlobals();
  const mgr = new CocoCommands(options.cwd as string);
  mgr.installCommands();
});
