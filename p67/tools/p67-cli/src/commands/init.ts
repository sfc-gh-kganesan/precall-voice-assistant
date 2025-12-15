import { Command } from 'commander';
import { CocoCommands } from '@p67-cli/coco/CocoCommands';
import { Workspace } from '@p67-cli/workspace/Workspace';
import { input, confirm } from '@inquirer/prompts';
import { mkdir } from 'node:fs/promises';
import * as yaml from 'js-yaml';
import * as fs from 'node:fs';
import * as path from 'node:path';

interface P67Config {
  runtime: {
    endpoint: string;
  };
  workflow: {
    entrypoint: string;
  };
}

export const initCommand = new Command('init')
  .description('Initialize a new p67 configuration file')
  .argument('[name]', 'Optional project name')
  .action(async (name?: string) => {
    const options = initCommand.optsWithGlobals();
    const targetDir = path.resolve(options.cwd as string, name || '');
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

    // Prompt for runtime service endpoint
    const endpoint = await input({
      message: 'Enter the runtime service endpoint URL',
      default: 'https://jnb46h6e-sfengineering-aifde.snowflakecomputing.app',
    });

    if (!endpoint || endpoint.trim() === '') {
      console.error('✗ Error: Runtime endpoint is required');
      process.exit(1);
    }

    // Create configuration object
    const config: P67Config = {
      runtime: {
        endpoint: endpoint.trim(),
      },
      workflow: {
        entrypoint: './dist/index.js',
      },
    };

    try {
      // Write configuration to YAML file
      const yamlContent = yaml.dump(config, {
        indent: 2,
        lineWidth: -1,
      });

      fs.writeFileSync(configPath, yamlContent, 'utf8');

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
