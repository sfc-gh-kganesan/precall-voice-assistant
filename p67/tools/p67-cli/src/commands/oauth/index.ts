import { Command } from '@p67-cli/Command';
import { connectCommand } from '@p67-cli/commands/oauth/connect.ts';
import { listCommand } from '@p67-cli/commands/oauth/list.ts';
import { refreshCommand } from '@p67-cli/commands/oauth/refresh.ts';
import { revokeCommand } from '@p67-cli/commands/oauth/revoke.ts';
import { connection } from '@p67-cli/middleware/connection';

export const oauthCommand = new Command('oauth')
    .description('Manage OAuth connections for external services')
    .use(connection)
    .addCommand(connectCommand)
    .addCommand(listCommand)
    .addCommand(refreshCommand)
    .addCommand(revokeCommand);
