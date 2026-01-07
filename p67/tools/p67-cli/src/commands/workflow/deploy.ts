import * as fs from 'node:fs';
import * as path from 'node:path';
import { Command } from '@p67-cli/Command.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { ctx } from '@p67-cli/context';

export const deployCommand = new Command('deploy')
    .description('Deploy a workflow from a zip file')
    .argument(
        '[filePath]',
        'Path to the workflow zip file (defaults to <buildDir>/workflow.zip)',
    )
    .action(async (filePath?: string) => {
        try {
            const { connection, projectConfig } = ctx();

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
                throw new Error(`✗ Error: File not found: ${resolvedPath}`);
            }

            // Check if it's a file (not a directory)
            const stats = fs.statSync(resolvedPath);
            if (!stats.isFile()) {
                throw new Error(`✗ Error: ${resolvedPath} is not a file`);
            }

            console.log(`Deploying workflow from: ${resolvedPath}\n`);

            // Read the file and create a Blob
            const fileBuffer = fs.readFileSync(resolvedPath);
            const blob = new Blob([fileBuffer], { type: 'application/zip' });
            const filename = path.basename(resolvedPath);

            const client = new ControldClient({
                baseUrl: connection.endpoint,
                pat: connection.pat,
            });

            const result = await client.createWorkflow(blob, filename);

            console.log('✓ Workflow deployed successfully!');
            console.log(`  Workflow ID: ${result.workflowId}`);
        } catch (error) {
            console.error(
                `Failed to deploy workflow from ${filePath || 'default location'}`,
            );
            throw error;
        }
    });
