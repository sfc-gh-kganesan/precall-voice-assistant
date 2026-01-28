import * as fs from 'node:fs';
import { mkdir } from 'node:fs/promises';
import * as path from 'node:path';
import { confirm } from '@inquirer/prompts';
import { Command } from '@p67-cli/Command';
import workflowEditorUi from '@p67-cli/project-root-template/workflow_editor_ui.html.src' with {
    type: 'file',
};
import workflowServer from '@p67-cli/project-root-template/workflow_server.py.src' with {
    type: 'file',
};
import { file } from 'bun';

export const createProjectRootCommand = new Command('createProjectRoot')
    .description(
        'Create a project root directory with workflow editor and server',
    )
    .argument('<my_projects_dir>', 'Project root directory path')
    .action(async (myProjectsDir: string) => {
        const targetDir = path.resolve(myProjectsDir);

        // Check if directory exists
        if (fs.existsSync(targetDir)) {
            const overwrite = await confirm({
                message: `Directory ${targetDir} already exists. Continue and overwrite files?`,
                default: false,
            });

            if (!overwrite) {
                console.log('✗ Operation cancelled');
                return;
            }
        } else {
            // Create directory
            try {
                await mkdir(targetDir, { recursive: true });
                console.log(`✓ Created directory: ${targetDir}`);
            } catch (error) {
                console.error('✗ Error creating directory:', error);
                return;
            }
        }

        // Copy workflow_editor_ui.html
        try {
            const editorContent = await file(workflowEditorUi).text();
            const editorPath = path.join(targetDir, 'workflow_editor_ui.html');
            await Bun.write(editorPath, editorContent);
            console.log('✓ Copied workflow_editor_ui.html');
        } catch (error) {
            console.error('✗ Error copying workflow_editor_ui.html:', error);
            return;
        }

        // Copy workflow_server.py
        try {
            const serverContent = await file(workflowServer).text();
            const serverPath = path.join(targetDir, 'workflow_server.py');
            await Bun.write(serverPath, serverContent);
            console.log('✓ Copied workflow_server.py');
        } catch (error) {
            console.error('✗ Error copying workflow_server.py:', error);
            return;
        }

        console.log('\n✓ Project root created successfully!');
        console.log(`  Location: ${targetDir}`);
        console.log('\nFiles created:');
        console.log('  - workflow_editor_ui.html');
        console.log('  - workflow_server.py');

        // Check if uv is available
        console.log('\nInitializing Python environment...');
        try {
            const uvCheckResult = Bun.spawnSync(['which', 'uv'], {
                stdout: 'ignore',
                stderr: 'ignore',
            });

            if (uvCheckResult.exitCode !== 0) {
                console.log(
                    '\n⚠ uv not found in PATH. Skipping Python dependency installation.',
                );
                console.log(
                    '  Please install uv (https://docs.astral.sh/uv/) and run:',
                );
                console.log(`  cd ${targetDir}`);
                console.log('  uv init');
                console.log('  uv add fastapi uvicorn');
                return;
            }
        } catch {
            console.log(
                '\n⚠ Could not check for uv. Skipping Python dependency installation.',
            );
            return;
        }

        // Run uv init
        console.log('Running uv init...');
        const uvInitProc = Bun.spawn(['uv', 'init', '--no-readme'], {
            cwd: targetDir,
            stdout: 'inherit',
            stderr: 'inherit',
        });

        const uvInitExitCode = await uvInitProc.exited;

        if (uvInitExitCode !== 0) {
            console.error('\n✗ Failed to run uv init');
            return;
        }

        // Run uv add fastapi uvicorn
        console.log('\nInstalling Python dependencies (fastapi, uvicorn)...');
        const uvAddProc = Bun.spawn(['uv', 'add', 'fastapi', 'uvicorn'], {
            cwd: targetDir,
            stdout: 'inherit',
            stderr: 'inherit',
        });

        const uvAddExitCode = await uvAddProc.exited;

        if (uvAddExitCode === 0) {
            console.log('\n✓ Python dependencies installed successfully!');
        } else {
            console.error(
                '\n✗ Failed to install Python dependencies. Please run manually:',
            );
            console.log(`  cd ${targetDir}`);
            console.log('  uv add fastapi uvicorn');
        }

        console.log('\n✓ Setup complete!');
        console.log('\nTo start the workflow server:');
        console.log(`  cd ${targetDir}`);
        console.log('  python workflow_server.py');
    });
