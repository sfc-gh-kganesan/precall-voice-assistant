import { Command } from 'commander';
import { getSnowflakePat } from '../secrets/1password.ts';

export const envCommand = new Command('env')
  .description('Print environment configuration for debugging')
  .action(async () => {
    try {
      const pat = getSnowflakePat();

      const data = {
        'Snowflake PAT': pat.value,
      };

      // Print the configuration
      console.log('\nConfiguration:\n');
      console.log(JSON.stringify(data, null, 2));
    } catch (error) {
      if (error instanceof Error) {
        console.error('✗ Error retrieving PAT from 1Password:', error.message);
      } else {
        console.error('✗ Error retrieving PAT from 1Password:', error);
      }
      process.exit(1);
    }
  });
