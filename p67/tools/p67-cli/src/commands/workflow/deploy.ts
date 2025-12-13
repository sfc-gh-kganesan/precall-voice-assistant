import { Command } from 'commander';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { ProjectConfig } from '../../config/ProjectConfig.ts';
import { ControldClient } from '../../clients/ControldClient.ts';
import { getSnowflakePat } from '../../secrets/1password.ts';

export const deployCommand = new Command('deploy')
  .description('Deploy a workflow from a zip file')
  .argument('<filePath>', 'Path to the workflow zip file')
  .action(async (filePath: string) => {
    try {
      const options = deployCommand.optsWithGlobals();
      const config = new ProjectConfig(options.cwd as string);

      if (!config.exists()) {
        console.error('✗ Error: p67.yml configuration file not found');
        console.error('  Run "p67 init" to create a configuration file');
        process.exit(1);
      }

      const pat = getSnowflakePat();
      if (!pat.value) {
        console.error('Unable to load Snowflake PAT from 1password.');
        process.exit(1);
      }

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

      const endpoint = config.getRuntimeEndpoint();
      const client = new ControldClient({ baseUrl: endpoint, pat: pat.value });

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
