import { config as dotenvConfig } from 'dotenv';

dotenvConfig();

export type ServerConfig = {
  port: number;
  nodeEnv: string;
};

export const loadConfig = (): ServerConfig => {
  return {
    port: parseInt(process.env.PORT || '3003'),
    nodeEnv: process.env.NODE_ENV || 'development',
  };
};
