import * as fs from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { Command } from '@p67-cli/Command.ts';
import { ctx } from '@p67-cli/context';
import { projectConfig } from '@p67-cli/middleware/project-config';

export const buildCommand = new Command('build')
	.description('Build the project')
	.use(projectConfig)
	.action(async () => {
		const { entrypoint, buildDir } = ctx().projectConfig;

		// Check if directory exists
		if (!fs.existsSync(buildDir)) {
			await mkdir(buildDir, { recursive: true });
		}

		try {
			const result = await Bun.build({
				entrypoints: [entrypoint],
				target: 'node',
				format: 'esm',
				outdir: buildDir,
				sourcemap: true,
			});

			if (result.success && result.outputs.length) {
				for (const output of result.outputs) {
					console.log(`✔︎ Created ${output.path}`);
				}
			}
		} catch (error) {
			console.error('Build failed:', error);
			throw error;
		}
	});
