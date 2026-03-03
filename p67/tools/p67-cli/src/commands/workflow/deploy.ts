import * as fs from 'node:fs';
import * as path from 'node:path';
import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { DotP67Config } from '@p67-cli/config/DotP67Config.ts';
import { ctx } from '@p67-cli/context';
import { projectConfig } from '@p67-cli/middleware/project-config';

export const deployCommand = new Command('deploy')
    .use(projectConfig)
    .option('--overwrite [boolean]', 'Overwrite existing workflow if it exists')
    .description('Deploy a workflow from a zip file')
    .argument(
        '[filePath]',
        'Path to the workflow zip file (defaults to <buildDir>/workflow.zip)',
    )
    .action(
        async (
            filePath?: string,
            options?: { overwrite?: boolean | string },
        ) => {
            try {
                const { connection, projectConfig } = ctx();

                const dotP67Config = new DotP67Config(projectConfig.projectDir);

                // Default to buildDir/workflow.zip if no path provided
                const defaultPath = path.join(
                    projectConfig.buildDir,
                    'workflow.zip',
                );
                const targetPath = filePath || defaultPath;

                // Resolve the file path
                const resolvedPath = path.resolve(targetPath);

                // Check if file exists
                if (!fs.existsSync(resolvedPath)) {
                    throw new Error(`File not found: ${resolvedPath}`);
                }

                // Check if it's a file (not a directory)
                const stats = fs.statSync(resolvedPath);
                if (!stats.isFile()) {
                    throw new Error(`${resolvedPath} is not a file`);
                }

                console.log(`Deploying workflow from: ${resolvedPath}\n`);

                // Read the file and create a Blob
                const fileBuffer = fs.readFileSync(resolvedPath);
                const blob = new Blob([fileBuffer], {
                    type: 'application/zip',
                });
                const filename = path.basename(resolvedPath);

                const client = new ControldClient({
                    baseUrl: connection.endpoint,
                    pat: connection.pat,
                });

                // Handle both --overwrite (boolean true) and --overwrite true (string 'true')
                const existingWorkflowId = dotP67Config.get()?.workflowId;
                const overwrite =
                    (options?.overwrite === true ||
                        options?.overwrite === 'true') &&
                    existingWorkflowId !== undefined;
                if (overwrite) {
                    console.log('Overwriting existing workflow...');
                }
                const result = await client.createWorkflow(
                    blob,
                    filename,
                    overwrite ? existingWorkflowId : undefined,
                );

                console.log('Workflow deployed successfully!');
                console.log(`  Workflow ID: ${result.workflowId}`);
                if (result.isNewVersion && result.versionNumber) {
                    console.log(
                        `  Created version ${result.versionNumber} (use "p67 workflow versions <name>" to see all versions)`,
                    );
                }

                dotP67Config.setWorkflowId(result.workflowId);
                dotP67Config.write();
            } catch (error) {
                // Check if this is a workflow locked error from the API
                if (
                    error instanceof Error &&
                    error.message.includes('Cannot overwrite workflow') &&
                    error.message.includes('while it is executing')
                ) {
                    console.error(`\nError: ${error.message}`);
                    console.error(
                        '\nTip: Wait for the workflow execution to complete, or run without --overwrite to deploy as a new workflow.',
                    );
                    process.exit(1);
                }

                console.error(
                    `Failed to deploy workflow from ${filePath || 'default location'}`,
                );
                throw error;
            }
        },
    );
