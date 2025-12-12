import { Command } from 'commander';
import { input, confirm } from '@inquirer/prompts';
import * as yaml from 'js-yaml';
import * as fs from 'node:fs';
import * as path from 'node:path';

interface P67Config {
  runtime: {
    endpoint: string;
  };
}

export const initCommand = new Command('init')
  .description('Initialize a new p67 configuration file')
  .action(async () => {
    const options = initCommand.optsWithGlobals();
    const targetDir = path.resolve(options.cwd as string);
    const configPath = path.join(targetDir, 'p67.yml');

    // Check if directory exists
    if (!fs.existsSync(targetDir)) {
      console.error(`✗ Error: Directory ${targetDir} does not exist`);
      process.exit(1);
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

    console.log('\nInitializing P67 configuration...\n');

    // Prompt for runtime service endpoint
    const endpoint = await input({
      message: 'Enter the runtime service endpoint URL',
      default: 'https://jjb46h6e-sfengineering-aifde.snowflakecomputing.app',
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
      process.exit(1);
    }
  });
