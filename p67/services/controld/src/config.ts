import { config as dotenvConfig } from 'dotenv';

dotenvConfig();

export type Config = {
  port: number;
  nodeEnv: string;
};

export default function (): Config {
  return {
    port: parseInt(process.env.PORT || '3002'),
    nodeEnv: process.env.NODE_ENV || 'development',
  };
}
