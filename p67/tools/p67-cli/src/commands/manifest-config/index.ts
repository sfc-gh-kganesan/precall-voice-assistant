import { Command } from '@p67-cli/Command';
import { fromConnectionCommand } from '@p67-cli/commands/manifest-config/from-connection';

export const manifestCommand = new Command('manifest')
    .description('Manage manifest configuration')
    .addCommand(fromConnectionCommand);
