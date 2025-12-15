import { Command } from 'commander';
import { ProjectConfig } from '@p67-cli/config/ProjectConfig.ts';
import { ControldClient } from '@p67-cli/clients/ControldClient.ts';
import { getSnowflakePat } from '@p67-cli/secrets/1password.ts';

export const listCommand = new Command('list')
  .description('List all available workflows')
  .action(async () => {
    try {
      const options = listCommand.optsWithGlobals();
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

      const endpoint = config.getRuntimeEndpoint();
      const client = new ControldClient({ baseUrl: endpoint, pat: pat.value });
      const result = await client.listWorkflows();

      if (result.workflows.length === 0) {
        console.log('No workflows found.');
      } else {
        result.workflows.forEach((workflow) => {
          console.log(workflow);
        });
      }
    } catch (error) {
      if (error instanceof Error) {
        console.error('✗ Error:', error.message);
      } else {
        console.error('✗ Unexpected error:', error);
      }
      process.exit(1);
    }
  });
