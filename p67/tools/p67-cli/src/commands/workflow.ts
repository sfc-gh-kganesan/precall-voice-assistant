import { Command } from 'commander';
import { select } from '@inquirer/prompts';
import { ProjectConfig } from '../config/ProjectConfig.ts';
import { HarnessClient } from '../clients/HarnessClient.ts';
import { getSnowflakePat } from '../secrets/1password.ts';

const listCommand = new Command('list')
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
      const client = new HarnessClient({ baseUrl: endpoint, pat: pat.value });
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

const runCommand = new Command('run')
  .description('Run a workflow')
  .argument('[workflowId]', 'Workflow ID to run')
  .action(async (workflowId?: string) => {
    try {
      const options = runCommand.optsWithGlobals();
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
      const client = new HarnessClient({ baseUrl: endpoint, pat: pat.value });

      let selectedWorkflowId = workflowId;

      // If no workflow ID provided, prompt user to select one
      if (!selectedWorkflowId) {
        console.log('Fetching available workflows...\n');
        const result = await client.listWorkflows();

        if (result.workflows.length === 0) {
          console.error('✗ Error: No workflows found');
          process.exit(1);
        }

        selectedWorkflowId = await select({
          message: 'Select a workflow to run:',
          choices: result.workflows.map((wf) => ({
            value: wf,
            name: wf,
          })),
        });
      }

      console.log(`\nRunning workflow: ${selectedWorkflowId}\n`);

      const runResult = await client.runWorkflow(selectedWorkflowId);

      // Display results
      console.log('─'.repeat(50));
      console.log(`Exit Code: ${runResult.exitCode}`);
      console.log(`Success: ${runResult.success}`);
      console.log('─'.repeat(50));

      if (runResult.stdout) {
        console.log('\nStdout:');
        console.log(runResult.stdout);
      }

      if (runResult.stderr) {
        console.log('\nStderr:');
        console.error(runResult.stderr);
      }

      // Exit with the workflow's exit code
      process.exit(runResult.exitCode);
    } catch (error) {
      if (error instanceof Error) {
        console.error('✗ Error:', error.message);
      } else {
        console.error('✗ Unexpected error:', error);
      }
      process.exit(1);
    }
  });

export const workflowCommand = new Command('workflow')
  .description('Operate on workflows')
  .addCommand(listCommand)
  .addCommand(runCommand)
  .action(async () => {
    console.log('Not implemented.');
  });
