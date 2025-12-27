import * as fs from 'node:fs';
import { mkdir } from 'node:fs/promises';
import * as path from 'node:path';
import { confirm } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import { CocoCommands } from '@p67-cli/coco/CocoCommands';
import { ProjectConfig } from '@p67-cli/config/ProjectConfig';
import {
    type ProjectConfigOptions,
    type ProjectOptions,
    projectConfig,
} from '@p67-cli/middleware/project-config';
import { Workspace } from '@p67-cli/workspace/Workspace';

export const initCommand = new Command('init')
    .description('Initialize a new p67 configuration file')
    .argument('[name]', 'Optional project name')
    .use<ProjectConfigOptions>(projectConfig, {
        requireConfigFileToExist: false,
    })
    .action(async (name?: string) => {
        const options = initCommand.optsWithGlobals<ProjectOptions>();
        const targetDir = path.resolve(options.project as string, name || '');
        const configPath = path.join(targetDir, 'p67.yml');

        // Check if directory exists
        if (!fs.existsSync(targetDir)) {
            const createDir = await confirm({
                message: `Project directory ${targetDir} does not exist. Create?`,
                default: true,
            });

            if (!createDir) {
                console.log('✗ Initialization cancelled');
                return;
            }

            // Create directory
            await mkdir(targetDir, { recursive: true });
        }

        // Check if config file already exists
        if (fs.existsSync(configPath)) {
            const overwrite = await confirm({
                message: `Configuration file already exists at ${configPath}. Overwrite?`,
                default: false,
            });

            if (!overwrite) {
                console.log('✗ Initialization cancelled');
                return;
            }
        }

        const config = ProjectConfig.default(targetDir);

        try {
            config.write();
            console.log('\n✓ Configuration file created successfully!');
            console.log(`  Location: ${configPath}\n`);
        } catch (error) {
            console.error('✗ Error writing configuration file:', error);
            return;
        }

        // Initialize Cortex Code commands
        const mgr = new CocoCommands(targetDir);
        const res = await mgr.installCommands();

        for (const cmd of res.installedCommands) {
            console.log(`✔︎ Installed ${cmd}`);
        }

        // bootstrap workspace files
        const workspc = new Workspace(targetDir);
        await workspc.bootstrap();
    });
