import * as fs from 'node:fs';
import { mkdir } from 'node:fs/promises';
import * as path from 'node:path';
import { ProjectConfig } from '@p67-cli/config/ProjectConfig';
import type { GlobalOptions } from '@p67-cli/global-options.ts';
import { Command } from 'commander';

export const buildCommand = new Command('build')
	.description('Build the project')
	.action(async () => {
		const options = buildCommand.optsWithGlobals<GlobalOptions>();
		const config = new ProjectConfig(options.project);
		const entrypoint = path.resolve(options.project, config.entrypoint);
		const buildDir = path.resolve(options.project, config.buildDir);

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
			process.exit(1);
		}
	});
