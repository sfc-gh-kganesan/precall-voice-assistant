import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import defineWorkflowCommand from '@coco/commands/define-workflow.md' with {
	type: 'file',
};
import generateWorkflowCommand from '@coco/commands/generate-workflow.md' with {
	type: 'file',
};
import { file } from 'bun';

enum Command {
	DefineWorkflow = 'DefineWorkflow',
	GenerateWorkflow = 'GenerateWorkflow',
}

const commandMap: Record<Command, string> = {
	[Command.DefineWorkflow]: defineWorkflowCommand,
	[Command.GenerateWorkflow]: generateWorkflowCommand,
};

interface InstallResult {
	installedCommands: string[];
}

export class CocoCommands {
	private projectDir: string;

	constructor(projectDir: string) {
		this.projectDir = projectDir;
	}

	async installCommand(cmd: Command): Promise<string> {
		const cmdPath = commandMap[cmd];
		const src = await file(cmdPath).text();
		const match = src.match(/name: (.*)/);
		if (!match || match.length < 2) {
			throw new Error(
				`File ${cmdPath} is malformed. Command name is expected to be included in frontmatter.`,
			);
		}
		const cmdName = match[1];
		const cmdFile = join(this.commandDir, `${cmdName}.md`);
		await Bun.write(cmdFile, src);
		return cmdName ?? '<unknown>';
	}

	get commandDir(): string {
		return join(this.projectDir, '.claude', 'commands');
	}

	async ensureCommandDirExists() {
		await mkdir(this.commandDir, { recursive: true });
	}

	async installCommands(): Promise<InstallResult> {
		await this.ensureCommandDirExists();
		const res: InstallResult = {
			installedCommands: [],
		};

		res.installedCommands.push(
			await this.installCommand(Command.DefineWorkflow),
		);
		res.installedCommands.push(
			await this.installCommand(Command.GenerateWorkflow),
		);

		return res;
	}
}
