import { deployCommand } from '@p67-cli/commands/workflow/deploy.ts';
import { listCommand } from '@p67-cli/commands/workflow/list.ts';
import { runCommand } from '@p67-cli/commands/workflow/run.ts';
import {
	ConnectionEnabledCommand,
	connectionMiddleware,
} from '@p67-cli/middleware/connection';

const workflowCommand = new ConnectionEnabledCommand('workflow').description(
	'Operate on workflows',
);

connectionMiddleware(workflowCommand);

workflowCommand
	.addCommand(listCommand)
	.addCommand(runCommand)
	.addCommand(deployCommand);

export { workflowCommand };
