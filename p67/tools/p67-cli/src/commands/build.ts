import * as fs from 'node:fs';
import { copyFile, mkdir } from 'node:fs/promises';
import * as path from 'node:path';
import { Command } from '@p67-cli/Command.ts';
import { ctx } from '@p67-cli/context';
import { projectConfig } from '@p67-cli/middleware/project-config';
import { zipSync } from 'fflate';

export const buildCommand = new Command('build')
    .description('Build the project')
    .use(projectConfig)
    .action(async () => {
        const config = ctx().projectConfig;
        const { entrypoint, buildDir, projectDir } = config;

        // Clean buildDir if it exists
        if (fs.existsSync(buildDir)) {
            fs.rmSync(buildDir, { recursive: true, force: true });
            console.log(`✔︎ Cleaned ${buildDir}`);
        }

        // Create buildDir
        await mkdir(buildDir, { recursive: true });

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

        // Copy manifest.yalml to buildDir
        const manifestSrc = path.join(projectDir, 'manifest.yaml');
        const manifestDest = path.join(buildDir, 'manifest.yaml');

        if (fs.existsSync(manifestSrc)) {
            await copyFile(manifestSrc, manifestDest);
            console.log(`✔︎ Copied manifest.yaml to ${buildDir}`);
        } else {
            console.warn(
                `⚠ manifest.yml not found in ${projectDir}. Skipping copy.`,
            );
        }

        // Zip buildDir contents into workflow.zip
        const zipPath = path.join(buildDir, 'workflow.zip');
        const files: Record<string, Uint8Array> = {};

        // Read all files from buildDir
        const bundleFiles = fs.readdirSync(buildDir, { recursive: true });
        for (const file of bundleFiles) {
            const filePath = path.join(buildDir, file as string);
            const stat = fs.statSync(filePath);

            if (stat.isFile()) {
                const relativePath = path.relative(buildDir, filePath);
                files[relativePath] = fs.readFileSync(filePath);
            }
        }

        // Create zip
        const zipped = zipSync(files, { level: 9 });
        fs.writeFileSync(zipPath, zipped);
        console.log(`✔︎ Created ${zipPath}`);
    });
