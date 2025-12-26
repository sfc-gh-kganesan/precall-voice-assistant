import * as fs from 'node:fs';
import * as path from 'node:path';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import type { ConnectionEnabledCommand } from '@p67-cli/middleware/connection';
import { Command } from 'commander';

export const deployCommand = new Command('deploy')
	.description('Deploy a workflow from a zip file')
	.argument('<filePath>', 'Path to the workflow zip file')
	.action(async (filePath: string) => {
		try {
			const connection = (deployCommand.parent as ConnectionEnabledCommand)
				?.connection;
			// Resolve the file path
			const resolvedPath = path.resolve(filePath);

			// Check if file exists
			if (!fs.existsSync(resolvedPath)) {
				console.error(`✗ Error: File not found: ${resolvedPath}`);
				process.exit(1);
			}

			// Check if it's a file (not a directory)
			const stats = fs.statSync(resolvedPath);
			if (!stats.isFile()) {
				console.error(`✗ Error: ${resolvedPath} is not a file`);
				process.exit(1);
			}

			console.log(`Deploying workflow from: ${resolvedPath}\n`);

			// Read the file and create a Blob
			const fileBuffer = fs.readFileSync(resolvedPath);
			const blob = new Blob([fileBuffer], { type: 'application/zip' });
			const filename = path.basename(resolvedPath);

			const client = new ControldClient({
				baseUrl: connection?.endpoint ?? '',
				pat: connection?.pat ?? '',
			});

			const result = await client.createWorkflow(blob, filename);

			console.log('✓ Workflow deployed successfully!');
			console.log(`  Workflow ID: ${result.workflowId}`);
		} catch (error) {
			if (error instanceof Error) {
				console.error('✗ Error:', error.message);
			} else {
				console.error('✗ Unexpected error:', error);
			}
			process.exit(1);
		}
	});
