import * as fs from 'node:fs';
import { mkdir, rename } from 'node:fs/promises';
import * as path from 'node:path';
import { ProjectConfig } from '@p67-cli/config/ProjectConfig';
import { Command } from 'commander';

export const buildCommand = new Command('build')
	.description('Build the project')
	.action(async () => {
		const options = buildCommand.optsWithGlobals();
		const config = new ProjectConfig(options.cwd as string);
		const entrypoint = path.resolve(options.cwd, config.entrypoint);
		const outFile = path.resolve(options.cwd, config.buildTarget);
		const outDir = path.dirname(outFile);

		// Check if directory exists
		if (!fs.existsSync(outDir)) {
			await mkdir(outDir, { recursive: true });
		}

		try {
			const result = await Bun.build({
				entrypoints: [entrypoint],
				target: 'node',
				format: 'esm',
				outdir: outDir,
				sourcemap: true,
			});

			if (result.success) {
				// Ensure the output file was created and rename it, if needed,
				// to match the filename specified in the project config.
				//
				// Note: Bun.build() does not appear to support an outfile configuration
				// value. If it did, this step would not be needed.
				if (result.outputs.length) {
					console.log('Build completed successfully!');
					for (const output of result.outputs) {
						if (output.kind === 'entry-point') {
							if (output.path !== outFile) {
								try {
									console.log(`rename ${output.path} to ${outFile}`);
									await rename(output.path, outFile);
									break;
								} catch (err) {
									throw new Error(
										`Failed to rename built artifact ${output.path} to ${outFile}: ${err}`,
									);
								}
							}
						}
					}
				} else {
					throw new Error('No artifacts built');
				}
			} else {
				for (const log of result.logs) {
					console.log(log);
				}
				throw new Error();
			}
		} catch (error) {
			console.error('Build failed:', error);
			process.exit(1);
		}
	});
