import type { Command } from '@p67-cli/Command';
import { ProjectConfig } from '@p67-cli/config/ProjectConfig';
import { ctx } from '@p67-cli/context';

export interface ProjectOptions {
	project: string;
}

export interface ProjectConfigOptions {
	requireConfigFileToExist: boolean;
}

const defaultOpts: ProjectConfigOptions = {
	requireConfigFileToExist: true,
};

export function projectConfig(
	command: Command,
	opts?: ProjectConfigOptions,
): Command {
	opts = opts ?? defaultOpts;
	return command
		.option('-p, --project <path>', 'Target project directory', process.cwd())
		.hook('preAction', (action) => {
			const options = action.optsWithGlobals<ProjectOptions>();
			const config = new ProjectConfig(options.project);

			if (opts.requireConfigFileToExist && !config.exists()) {
				throw new Error(
					`project file ${config.configPath} not found.Try running "p67 init" to create a new project.`,
				);
			}

			ctx().projectConfig = config;
		});
}
