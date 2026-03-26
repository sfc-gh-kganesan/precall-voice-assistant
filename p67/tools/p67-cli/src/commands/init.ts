import * as fs from 'node:fs';
import { mkdir } from 'node:fs/promises';
import * as path from 'node:path';
import { confirm, select } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import { CocoCommands } from '@p67-cli/coco/CocoCommands';
import { ProjectConfig } from '@p67-cli/config/ProjectConfig';
import {
    type ProjectConfigOptions,
    type ProjectOptions,
    projectConfig,
} from '@p67-cli/middleware/project-config';
import {
    listTemplates,
    type WorkflowLanguage,
    Workspace,
} from '@p67-cli/workspace/Workspace';

export const initCommand = new Command('init')
    .description('Initialize a new p67 configuration file')
    .argument('[name]', 'Optional project name')
    .option(
        '-l, --language <language>',
        'Workflow language (typescript or python)',
    )
    .option(
        '-t, --template <name>',
        `Scaffold from a pre-built template (${listTemplates().join(', ')})`,
    )
    .use<ProjectConfigOptions>(projectConfig, {
        requireConfigFileToExist: false,
    })
    .action(async (name?: string) => {
        const options = initCommand.optsWithGlobals<
            ProjectOptions & { language?: string; template?: string }
        >();
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

        // Determine workflow language
        let language: WorkflowLanguage = 'typescript';
        if (options.language) {
            if (
                options.language !== 'typescript' &&
                options.language !== 'python'
            ) {
                console.error(
                    `✗ Invalid language: ${options.language}. Must be 'typescript' or 'python'.`,
                );
                return;
            }
            language = options.language as WorkflowLanguage;
        } else {
            // Prompt for language selection
            language = await select({
                message: 'Select workflow language:',
                choices: [
                    {
                        name: 'TypeScript',
                        value: 'typescript' as WorkflowLanguage,
                        description: 'Use TypeScript with Node.js runtime',
                    },
                    {
                        name: 'Python',
                        value: 'python' as WorkflowLanguage,
                        description: 'Use Python 3.9+ runtime',
                    },
                ],
                default: 'typescript',
            });
        }

        // Resolve template
        const template: string | undefined = options.template;
        if (template !== undefined) {
            const available = listTemplates();
            if (!available.includes(template)) {
                console.error(
                    `✗ Unknown template "${template}". Available templates: ${available.join(', ')}`,
                );
                return;
            }
        }

        console.log(`\nInitializing ${language} workflow project...`);

        const config = ProjectConfig.default(targetDir);

        try {
            config.write();
            console.log('\n✓ Configuration file created successfully!');
            console.log(`  Location: ${configPath}\n`);
        } catch (error) {
            console.error('✗ Error writing configuration file:', error);
            return;
        }

        // Initialize Cortex Code commands (only for TypeScript)
        if (language === 'typescript') {
            const mgr = new CocoCommands(targetDir);
            const res = await mgr.installCommands();

            for (const cmd of res.installedCommands) {
                console.log(`✔︎ Installed ${cmd}`);
            }
        }

        // bootstrap workspace files
        const workspc = new Workspace(targetDir, language);
        if (template) {
            await workspc.bootstrapTemplate(template);
            console.log(
                `✔︎ Created ${language} workflow from template "${template}"`,
            );
        } else {
            await workspc.bootstrap();
            console.log(`✔︎ Created ${language} workflow files`);
        }

        // Install dependencies based on language
        if (language === 'typescript') {
            // Check if npm is available
            try {
                const { exitCode } = Bun.spawnSync(['which', 'npm'], {
                    stdout: 'ignore',
                    stderr: 'ignore',
                });

                if (exitCode !== 0) {
                    console.log(
                        '\n⚠ npm not found in PATH. Skipping dependency installation.',
                    );
                    console.log(
                        '  Please install Node.js and npm, then run "npm install" in the project directory.',
                    );
                    return;
                }
            } catch {
                console.log(
                    '\n⚠ Could not check for npm. Skipping dependency installation.',
                );
                return;
            }

            // Install dependencies
            console.log('\nInstalling dependencies...');
            const installProc = Bun.spawn(['npm', 'install'], {
                cwd: targetDir,
                stdout: 'inherit',
                stderr: 'inherit',
            });

            const installExitCode = await installProc.exited;

            if (installExitCode === 0) {
                console.log('\n✓ Dependencies installed successfully!');
            } else {
                console.error(
                    '\n✗ Failed to install dependencies. Please run "npm install" manually.',
                );
            }
        } else {
            // Python - suggest pip install
            console.log('\n✓ Python workflow initialized!');
            console.log('\nNext steps:');
            console.log('  1. Create a virtual environment:');
            console.log('     python3 -m venv .venv');
            console.log('     source .venv/bin/activate');
            console.log('  2. Install dependencies:');
            console.log('     pip install -r requirements.txt');
            console.log(
                '  3. Configure manifest.yaml with your Snowflake connection',
            );
            console.log('  4. Build and deploy:');
            console.log('     p67 build && p67 workflow deploy');
        }
    });
